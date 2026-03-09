"""
API Router: News & Sentiment

Endpoints for scraped F1 news and sentiment analysis
"""
from fastapi import APIRouter, Query
from typing import Optional
from dataclasses import asdict

from services.news_scraper import scraper

router = APIRouter()


@router.get("/latest")
async def get_latest_news(
    limit: int = Query(default=30, ge=1, le=100),
    driver: Optional[str] = Query(default=None, description="Filter by driver code"),
    team: Optional[str] = Query(default=None, description="Filter by team name"),
):
    """Get latest scraped F1 news articles."""
    articles = await scraper.fetch_all_news(max_articles=limit * 2)

    # Filter
    if driver:
        articles = [a for a in articles if driver.upper() in a.drivers_mentioned]
    if team:
        articles = [a for a in articles if any(team.lower() in t.lower() for t in a.teams_mentioned)]

    return {
        "count": len(articles[:limit]),
        "articles": [asdict(a) for a in articles[:limit]],
    }


@router.get("/sentiment/drivers")
async def get_driver_sentiments():
    """Get aggregated sentiment per driver from recent news."""
    articles = await scraper.fetch_all_news(max_articles=100)
    sentiment_map = scraper.get_driver_sentiment(articles)

    result = []
    for code, ds in sorted(sentiment_map.items(), key=lambda x: x[1].avg_sentiment, reverse=True):
        result.append({
            "driver_code": code,
            "articles_count": ds.articles_count,
            "positive": ds.positive_count,
            "negative": ds.negative_count,
            "neutral": ds.neutral_count,
            "avg_sentiment": ds.avg_sentiment,
            "sentiment_label": ds.sentiment_label,
            "headlines": ds.headlines[:3],
        })

    return {"drivers": result, "total_articles": len(articles)}


@router.get("/sentiment/teams")
async def get_team_sentiments():
    """Get aggregated sentiment per team from recent news."""
    articles = await scraper.fetch_all_news(max_articles=100)
    team_map = scraper.get_team_sentiment(articles)

    return {
        "teams": [
            {"team": team, "avg_sentiment": score}
            for team, score in sorted(team_map.items(), key=lambda x: x[1], reverse=True)
        ],
        "total_articles": len(articles),
    }


@router.get("/prediction-context")
async def get_prediction_context(
    season: int = Query(...),
    round: int = Query(default=1),
):
    """
    Get news-derived context to enhance ML predictions.
    Returns sentiment scores per driver + team that can be fed
    into the prediction model as additional features.
    """
    articles = await scraper.fetch_all_news(max_articles=100)
    driver_sentiment = scraper.get_driver_sentiment(articles)
    team_sentiment = scraper.get_team_sentiment(articles)

    # News-derived features per driver
    driver_features = {}
    for code, ds in driver_sentiment.items():
        driver_features[code] = {
            "news_sentiment": ds.avg_sentiment,
            "news_volume": min(ds.articles_count / 10.0, 1.0),  # Normalized 0-1
            "positive_ratio": ds.positive_count / max(ds.articles_count, 1),
            "negative_ratio": ds.negative_count / max(ds.articles_count, 1),
        }

    return {
        "season": season,
        "round": round,
        "driver_features": driver_features,
        "team_sentiment": team_sentiment,
        "articles_analyzed": len(articles),
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
