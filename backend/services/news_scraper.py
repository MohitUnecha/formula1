"""
F1 News Scraper & Sentiment Analyzer

Scrapes latest F1 news from multiple sources and extracts sentiment/context
to enhance ML prediction model with real-world intelligence.

Sources:
  - Formula1.com RSS feed
  - ESPN F1 RSS feed  
  - Autosport RSS feed
"""

import re
import time
import hashlib
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ─── Sentiment Keywords ───────────────────────────────────────────────────────

POSITIVE_KEYWORDS = {
    "win", "wins", "won", "victory", "dominant", "fastest", "pole", "podium",
    "upgrade", "improved", "strong", "confident", "optimistic", "impressive",
    "brilliant", "masterclass", "stunning", "incredible", "record", "leading",
    "champion", "title", "breakthrough", "momentum", "top", "fastest lap",
    "front row", "clean sweep", "hat trick", "unstoppable", "resurgence",
    "comeback", "secure", "clinch", "dominate", "perfect", "outstanding",
}

NEGATIVE_KEYWORDS = {
    "crash", "penalty", "dnf", "retired", "engine failure", "gearbox",
    "disqualified", "investigation", "struggling", "slow", "disappointing",
    "poor", "worst", "grid penalty", "pit stop error", "collision",
    "spin", "damage", "injury", "miss", "ruled out", "withdraw",
    "sanction", "controversy", "banned", "demoted", "underperforming",
    "reliability", "issues", "problem", "setback", "deficit", "complaints",
}

NEUTRAL_KEYWORDS = {
    "contract", "move", "transfer", "announce", "confirm", "team orders",
    "strategy", "regulations", "rule change", "budget cap", "testing",
}

# ─── Driver name variations for entity extraction ─────────────────────────────

DRIVER_ALIASES: Dict[str, List[str]] = {
    "VER": ["verstappen", "max verstappen", "max"],
    "HAM": ["hamilton", "lewis hamilton", "lewis"],
    "LEC": ["leclerc", "charles leclerc", "charles"],
    "NOR": ["norris", "lando norris", "lando"],
    "SAI": ["sainz", "carlos sainz", "carlos"],
    "PIA": ["piastri", "oscar piastri", "oscar"],
    "RUS": ["russell", "george russell", "george"],
    "PER": ["perez", "sergio perez", "checo"],
    "ALO": ["alonso", "fernando alonso", "fernando"],
    "STR": ["stroll", "lance stroll", "lance"],
    "GAS": ["gasly", "pierre gasly", "pierre"],
    "OCO": ["ocon", "esteban ocon"],
    "TSU": ["tsunoda", "yuki tsunoda", "yuki"],
    "RIC": ["ricciardo", "daniel ricciardo", "daniel"],
    "BOT": ["bottas", "valtteri bottas", "valtteri"],
    "ZHO": ["zhou", "guanyu zhou"],
    "MAG": ["magnussen", "kevin magnussen", "kevin"],
    "HUL": ["hulkenberg", "nico hulkenberg", "nico hulk"],
    "ALB": ["albon", "alex albon", "alex"],
    "SAR": ["sargeant", "logan sargeant", "logan"],
    "BEA": ["bearman", "oliver bearman"],
    "LAW": ["lawson", "liam lawson"],
    "COL": ["colapinto", "franco colapinto"],
    "DOO": ["doohan", "jack doohan"],
    "ANT": ["antonelli", "andrea kimi antonelli", "antonelli"],
    "HAD": ["hadjar", "isack hadjar"],
    "BOR": ["bortoleto", "gabriel bortoleto"],
}

TEAM_ALIASES: Dict[str, List[str]] = {
    "Red Bull Racing": ["red bull", "redbull", "rbr"],
    "Ferrari": ["ferrari", "scuderia ferrari"],
    "McLaren": ["mclaren"],
    "Mercedes": ["mercedes", "merc"],
    "Aston Martin": ["aston martin", "aston"],
    "Alpine": ["alpine"],
    "Williams": ["williams"],
    "RB": ["rb", "racing bulls", "visa cashapp rb"],
    "Kick Sauber": ["sauber", "kick sauber", "stake"],
    "Haas": ["haas"],
}


@dataclass
class NewsArticle:
    title: str
    summary: str
    source: str
    url: str
    published: Optional[str] = None
    sentiment_score: float = 0.0  # -1.0 to +1.0
    drivers_mentioned: List[str] = field(default_factory=list)
    teams_mentioned: List[str] = field(default_factory=list)
    article_hash: str = ""

    def __post_init__(self):
        if not self.article_hash:
            self.article_hash = hashlib.md5(
                (self.title + self.url).encode()
            ).hexdigest()[:12]


@dataclass
class DriverNewsSentiment:
    driver_code: str
    articles_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    avg_sentiment: float = 0.0
    headlines: List[str] = field(default_factory=list)

    @property
    def sentiment_label(self) -> str:
        if self.avg_sentiment > 0.15:
            return "positive"
        elif self.avg_sentiment < -0.15:
            return "negative"
        return "neutral"


# ─── RSS / Web Scraping ──────────────────────────────────────────────────────


class F1NewsScraper:
    """Scrapes F1 news from RSS feeds and web sources."""

    RSS_FEEDS = [
        ("https://www.formula1.com/content/fom-website/en/latest/all.xml", "Formula1.com"),
        ("https://www.autosport.com/rss/feed/f1", "Autosport"),
        ("https://www.motorsport.com/rss/f1/news/", "Motorsport.com"),
    ]

    # Fallback: scrape HTML if RSS fails
    FALLBACK_URLS = [
        ("https://www.formula1.com/en/latest/all", "Formula1.com"),
        ("https://www.skysports.com/f1/news", "Sky Sports F1"),
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, cache_ttl: int = 900):
        """
        Args:
            cache_ttl: Seconds to cache results (default 15 minutes)
        """
        self._cache: Dict[str, List[NewsArticle]] = {}
        self._cache_time: Dict[str, float] = {}
        self._cache_ttl = cache_ttl

    def _is_cached(self, key: str) -> bool:
        return (
            key in self._cache
            and (time.time() - self._cache_time.get(key, 0)) < self._cache_ttl
        )

    async def fetch_all_news(self, max_articles: int = 50) -> List[NewsArticle]:
        """Fetch news from all sources, with caching."""

        cache_key = "all_news"
        if self._is_cached(cache_key):
            return self._cache[cache_key][:max_articles]

        articles: List[NewsArticle] = []

        # Try RSS feeds first
        for feed_url, source in self.RSS_FEEDS:
            try:
                feed_articles = await self._parse_rss(feed_url, source)
                articles.extend(feed_articles)
                logger.info(f"Fetched {len(feed_articles)} articles from {source} RSS")
            except Exception as e:
                logger.warning(f"RSS failed for {source}: {e}")

        # If we got very few articles, try HTML scraping
        if len(articles) < 5:
            for page_url, source in self.FALLBACK_URLS:
                try:
                    html_articles = await self._scrape_html(page_url, source)
                    articles.extend(html_articles)
                    logger.info(f"Scraped {len(html_articles)} articles from {source}")
                except Exception as e:
                    logger.warning(f"HTML scrape failed for {source}: {e}")

        # Deduplicate by hash
        seen = set()
        unique = []
        for a in articles:
            if a.article_hash not in seen:
                seen.add(a.article_hash)
                # Analyze sentiment & entities
                self._analyze_article(a)
                unique.append(a)

        unique.sort(key=lambda a: a.published or "", reverse=True)

        self._cache[cache_key] = unique
        self._cache_time[cache_key] = time.time()

        return unique[:max_articles]

    async def _parse_rss(self, url: str, source: str) -> List[NewsArticle]:
        """Parse an RSS/XML feed."""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=self.HEADERS) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []

        for item in soup.find_all("item"):
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            pub_el = item.find("pubdate") or item.find("pubDate")

            title = title_el.get_text(strip=True) if title_el else ""
            desc = desc_el.get_text(strip=True) if desc_el else ""
            link = link_el.get_text(strip=True) if link_el else ""
            pub = pub_el.get_text(strip=True) if pub_el else ""

            if title:
                articles.append(NewsArticle(
                    title=title,
                    summary=desc[:300],
                    source=source,
                    url=link,
                    published=pub,
                ))

        return articles[:30]

    async def _scrape_html(self, url: str, source: str) -> List[NewsArticle]:
        """Scrape news from an HTML page (fallback)."""
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=self.HEADERS) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []

        # Generic scraping: look for article headlines
        for tag in soup.find_all(["article", "div"], class_=re.compile(r"news|article|story|headline", re.I)):
            heading = tag.find(["h1", "h2", "h3", "h4", "a"])
            if heading:
                title = heading.get_text(strip=True)
                link = ""
                a_tag = heading if heading.name == "a" else heading.find("a")
                if a_tag and a_tag.get("href"):
                    link = a_tag["href"]
                    if link.startswith("/"):
                        # Resolve relative URL
                        from urllib.parse import urljoin
                        link = urljoin(url, link)

                summary_el = tag.find("p")
                summary = summary_el.get_text(strip=True)[:300] if summary_el else ""

                if title and len(title) > 10:
                    articles.append(NewsArticle(
                        title=title,
                        summary=summary,
                        source=source,
                        url=link,
                    ))

        return articles[:20]

    def _analyze_article(self, article: NewsArticle):
        """Compute sentiment score and extract driver/team mentions."""
        text = (article.title + " " + article.summary).lower()

        # Sentiment scoring
        pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
        neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
        total = pos + neg
        if total > 0:
            article.sentiment_score = round((pos - neg) / total, 3)
        else:
            article.sentiment_score = 0.0

        # Driver extraction
        for code, aliases in DRIVER_ALIASES.items():
            if any(alias in text for alias in aliases):
                article.drivers_mentioned.append(code)

        # Team extraction
        for team, aliases in TEAM_ALIASES.items():
            if any(alias in text for alias in aliases):
                article.teams_mentioned.append(team)

    def get_driver_sentiment(
        self, articles: List[NewsArticle]
    ) -> Dict[str, DriverNewsSentiment]:
        """Aggregate per-driver sentiment from scraped articles."""
        driver_map: Dict[str, DriverNewsSentiment] = {}

        for article in articles:
            for code in article.drivers_mentioned:
                if code not in driver_map:
                    driver_map[code] = DriverNewsSentiment(driver_code=code)

                ds = driver_map[code]
                ds.articles_count += 1
                ds.headlines.append(article.title)

                if article.sentiment_score > 0.1:
                    ds.positive_count += 1
                elif article.sentiment_score < -0.1:
                    ds.negative_count += 1
                else:
                    ds.neutral_count += 1

        # Compute averages
        for ds in driver_map.values():
            if ds.articles_count > 0:
                total_sent = (ds.positive_count - ds.negative_count) / ds.articles_count
                ds.avg_sentiment = round(total_sent, 3)
            ds.headlines = ds.headlines[:5]  # Keep top 5 headlines

        return driver_map

    def get_team_sentiment(
        self, articles: List[NewsArticle]
    ) -> Dict[str, float]:
        """Aggregate per-team sentiment from articles."""
        team_scores: Dict[str, List[float]] = {}

        for article in articles:
            for team in article.teams_mentioned:
                if team not in team_scores:
                    team_scores[team] = []
                team_scores[team].append(article.sentiment_score)

        return {
            team: round(sum(scores) / len(scores), 3)
            for team, scores in team_scores.items()
            if scores
        }


# ─── Singleton instance ──────────────────────────────────────────────────────
scraper = F1NewsScraper()
