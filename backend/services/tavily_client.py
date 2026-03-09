"""
Tavily Search Client for F1 Predictions

Uses Tavily AI search API to gather real-time web context for current event predictions.
Rate-limited — only activated for current season events on the predictions page.
Falls back gracefully to Groq-only predictions if Tavily fails or quota exhausted.

API: https://tavily.com

CACHING: Results are cached in SQLite (NewsCache table) to reduce API usage.
Cache expires after 24 hours by default. Hit count is tracked for analytics.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Cache settings
CACHE_EXPIRY_HOURS = 24  # How long to keep cached results
CACHE_ENABLED = True


@dataclass
class TavilySearchResult:
    """Structured result from a Tavily search."""
    query: str
    results: List[Dict[str, Any]]
    summary: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None

    def to_context_string(self, max_chars: int = 1500) -> str:
        """Flatten search results into a context string for LLM consumption."""
        if self.error:
            return ""
        parts: List[str] = []
        if self.summary:
            parts.append(f"Web Summary: {self.summary}")
        for r in self.results[:5]:
            title = r.get("title", "")
            content = r.get("content", "")[:300]
            if title:
                parts.append(f"- {title}: {content}")
        text = "\n".join(parts)
        return text[:max_chars]

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class TavilyClient:
    """Lightweight async Tavily search client with rate limiting and database caching."""

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self):
        self.api_key: Optional[str] = getattr(settings, "tavily_api_key", None)
        self.timeout: float = getattr(settings, "tavily_timeout", 15.0)
        self._last_request: float = 0.0
        self._min_interval: float = 1.0  # 1s between requests to conserve quota
        self._error_count: int = 0
        self._max_errors: int = 5  # disable after 5 consecutive errors (quota likely exhausted)
        self._disabled: bool = False

    @property
    def available(self) -> bool:
        """Check if Tavily is available and not disabled."""
        return bool(self.api_key) and not self._disabled

    def _get_cached_result(self, query: str, db_session) -> Optional[TavilySearchResult]:
        """Check database cache for existing results."""
        if not CACHE_ENABLED or db_session is None:
            return None
        
        try:
            from models import NewsCache
            
            # Find non-expired cache entry
            cache_entry = db_session.query(NewsCache).filter(
                NewsCache.query == query,
                NewsCache.source == "tavily",
                NewsCache.expires_at > datetime.utcnow()
            ).first()
            
            if cache_entry:
                # Increment hit count
                cache_entry.hit_count = (cache_entry.hit_count or 0) + 1
                db_session.commit()
                
                # Reconstruct TavilySearchResult from cache
                results = json.loads(cache_entry.results_json) if cache_entry.results_json else []
                logger.info(f"Tavily cache HIT for query: {query[:50]}... (hits: {cache_entry.hit_count})")
                
                return TavilySearchResult(
                    query=query,
                    results=results,
                    summary=cache_entry.summary,
                    latency_ms=0.0,  # Cached result, no API latency
                )
            return None
        except Exception as exc:
            logger.warning(f"Cache lookup error: {exc}")
            return None

    def _store_in_cache(self, query: str, result: TavilySearchResult, db_session) -> None:
        """Store search results in database cache."""
        if not CACHE_ENABLED or db_session is None or result.error:
            return
        
        try:
            from models import NewsCache
            
            # Check if entry already exists
            existing = db_session.query(NewsCache).filter(
                NewsCache.query == query,
                NewsCache.source == "tavily"
            ).first()
            
            if existing:
                # Update existing entry
                existing.results_json = json.dumps(result.results)
                existing.summary = result.summary
                existing.expires_at = datetime.utcnow() + timedelta(hours=CACHE_EXPIRY_HOURS)
                existing.created_at = datetime.utcnow()
                existing.hit_count = 0
            else:
                # Create new entry
                cache_entry = NewsCache(
                    query=query,
                    source="tavily",
                    results_json=json.dumps(result.results),
                    summary=result.summary,
                    expires_at=datetime.utcnow() + timedelta(hours=CACHE_EXPIRY_HOURS),
                    hit_count=0,
                )
                db_session.add(cache_entry)
            
            db_session.commit()
            logger.info(f"Tavily result cached for query: {query[:50]}... (expires in {CACHE_EXPIRY_HOURS}h)")
        except Exception as exc:
            logger.warning(f"Cache storage error: {exc}")
            db_session.rollback()

    async def search(self, query: str, max_results: int = 5, db_session=None) -> TavilySearchResult:
        """
        Search Tavily for real-time web context.
        Returns TavilySearchResult; on failure, error field is populated.
        
        Uses database cache to reduce API calls. Pass db_session from FastAPI endpoint.
        """
        # Check cache first
        cached = self._get_cached_result(query, db_session)
        if cached:
            return cached
        
        if not self.api_key:
            return TavilySearchResult(query=query, results=[], error="Tavily API key not configured")

        if self._disabled:
            return TavilySearchResult(query=query, results=[], error="Tavily disabled due to repeated errors (quota likely exhausted)")

        # Rate limiting
        now = time.monotonic()
        wait = self._min_interval - (now - self._last_request)
        if wait > 0:
            import asyncio
            await asyncio.sleep(wait)

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.BASE_URL, json=payload)
            self._last_request = time.monotonic()
            latency = (time.monotonic() - start) * 1000

            if resp.status_code == 429:
                self._error_count += 1
                if self._error_count >= self._max_errors:
                    self._disabled = True
                    logger.warning("Tavily disabled: rate limit exceeded repeatedly")
                return TavilySearchResult(query=query, results=[], error=f"Tavily rate limited (429)", latency_ms=latency)

            if resp.status_code != 200:
                self._error_count += 1
                if self._error_count >= self._max_errors:
                    self._disabled = True
                return TavilySearchResult(query=query, results=[], error=f"Tavily HTTP {resp.status_code}: {resp.text[:200]}", latency_ms=latency)

            data = resp.json()
            self._error_count = 0  # reset on success

            results = data.get("results", [])
            answer = data.get("answer")

            result = TavilySearchResult(
                query=query,
                results=results,
                summary=answer,
                latency_ms=latency,
            )
            
            # Cache the successful result
            self._store_in_cache(query, result, db_session)
            
            return result

        except Exception as exc:
            self._error_count += 1
            if self._error_count >= self._max_errors:
                self._disabled = True
                logger.warning(f"Tavily disabled after {self._max_errors} consecutive errors: {exc}")
            return TavilySearchResult(query=query, results=[], error=str(exc))

    async def search_f1_prediction_context(
        self,
        event_name: str,
        season: int,
        round_num: int,
        driver_codes: Optional[List[str]] = None,
        db_session=None,
    ) -> TavilySearchResult:
        """
        Specialized search for F1 race prediction context.
        Only used for current season events.
        
        Args:
            event_name: Name of the race (e.g., "Monaco Grand Prix")
            season: Year of the race
            round_num: Round number in the season
            driver_codes: Optional list of driver codes for focused search
            db_session: Database session for caching
        """
        current_year = datetime.utcnow().year

        # Only activate for current season events
        if season < current_year:
            return TavilySearchResult(
                query="",
                results=[],
                error=f"Tavily only active for current season ({current_year}), requested {season}",
            )

        query_parts = [f"F1 {season} {event_name} race prediction"]
        if driver_codes:
            top_drivers = ", ".join(driver_codes[:5])
            query_parts.append(f"favorites: {top_drivers}")
        query_parts.append("odds form analysis")

        query = " ".join(query_parts)
        return await self.search(query, max_results=5, db_session=db_session)


# Module-level singleton
tavily_client = TavilyClient()
