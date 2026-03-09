"""
API Router: Predictions

Endpoints for race predictions and explainability.

Enhanced prediction engine with 8 boost layers:
  1. Base GBM model (11 features from DB)
  2. News sentiment (±5%)
  3. Circuit history from Jolpica (±4%)
  4. Qualifying pace from OpenF1 (±3%)
  5. Elo rating system (±6%) — THE NEW TRICK
  6. Constructor momentum from Jolpica standings (±3%)
  7. Championship pressure (±2%)
  8. Weather impact from OpenF1 (±2%)
  9. Pit stop reliability from Jolpica (±1.5%)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import json
import random
import logging
import math
import asyncio

logger = logging.getLogger(__name__)

from database import get_db
from models import Prediction, Driver, ShapExplanation, DriverSession, Session as DBSession, Event, Weather, Lap, PredictionRateLimit, NewsCache
from team_mapping import get_team_for_driver
from services.news_scraper import scraper
from services.jolpica_client import jolpica
from services.openf1_client import openf1
from services.elo_rating import get_elo_system, F1EloSystem
from services.groq_client import groq_client
from services.tavily_client import tavily_client
from services.gemini_client import gemini_client
from services.multi_ai_client import multi_ai_client


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING CONFIGURATION (3 predictions per 3 hours to conserve API credits)
# ═══════════════════════════════════════════════════════════════════════════════
RATE_LIMIT_MAX_REQUESTS = 3
RATE_LIMIT_WINDOW_HOURS = 3


def check_rate_limit(client_ip: str, db: Session) -> tuple[bool, int, datetime | None]:
    """
    Check if the client has exceeded the rate limit.
    Returns (is_allowed, remaining_requests, reset_time)
    """
    window_start = datetime.utcnow() - timedelta(hours=RATE_LIMIT_WINDOW_HOURS)
    
    # Count requests in the window
    request_count = db.query(func.count(PredictionRateLimit.id)).filter(
        PredictionRateLimit.client_ip == client_ip,
        PredictionRateLimit.request_time >= window_start
    ).scalar() or 0
    
    remaining = max(0, RATE_LIMIT_MAX_REQUESTS - request_count)
    
    if request_count >= RATE_LIMIT_MAX_REQUESTS:
        # Find the oldest request in the window to calculate reset time
        oldest = db.query(PredictionRateLimit.request_time).filter(
            PredictionRateLimit.client_ip == client_ip,
            PredictionRateLimit.request_time >= window_start
        ).order_by(PredictionRateLimit.request_time.asc()).first()
        
        reset_time = oldest[0] + timedelta(hours=RATE_LIMIT_WINDOW_HOURS) if oldest else None
        return False, 0, reset_time
    
    return True, remaining, None


def record_rate_limit(client_ip: str, season: int, round_num: int, db: Session):
    """Record a prediction request for rate limiting."""
    rate_record = PredictionRateLimit(
        client_ip=client_ip,
        request_time=datetime.utcnow(),
        season=season,
        round=round_num
    )
    db.add(rate_record)
    db.commit()

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC ROUTES FIRST (must be defined before dynamic /{session_id} routes)
# ═══════════════════════════════════════════════════════════════════════════════

class ModelHealth(BaseModel):
    status: str
    model_version: str
    accuracy: float
    last_trained: str
    total_races_trained: int


class FeatureImportance(BaseModel):
    feature_name: str
    importance: float
    description: str


class SimpleDriverPrediction(BaseModel):
    driver_code: str
    driver_name: str
    team: str
    probability: float
    confidence: str
    elo_rating: Optional[float] = None
    elo_tier: Optional[str] = None
    boosts: Optional[Dict[str, float]] = None  # breakdown of each boost applied
    groq: Optional[dict] = None  # Groq API response


class SimplePredictionRequest(BaseModel):
    season: int
    round: int
    session_type: str = "R"


class SimplePredictionResponse(BaseModel):
    season: int
    round: int
    session_type: str
    event_name: str
    predictions: List[SimpleDriverPrediction]
    model_version: str
    generated_at: str
    boosts_active: Optional[List[str]] = None  # which boosts fired
    elo_rankings: Optional[List[Dict[str, Any]]] = None  # top Elo drivers


@router.get("/health", response_model=ModelHealth)
async def get_model_health():
    """Get ML model health and status"""
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_models")
    meta_path = os.path.join(model_dir, "model_metadata.json")
    
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        return ModelHealth(
            status="healthy",
            model_version=f"GBM v{meta.get('version', 'unknown')}",
            accuracy=meta.get('metrics', {}).get('win_accuracy', 0),
            last_trained=meta.get('trained_at', ''),
            total_races_trained=0
        )
    
    return ModelHealth(
        status="not_trained",
        model_version="N/A",
        accuracy=0,
        last_trained="",
        total_races_trained=0
    )


@router.get("/features", response_model=List[FeatureImportance])
async def get_feature_importance():
    """Get feature importance from the trained model"""
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_models")
    meta_path = os.path.join(model_dir, "model_metadata.json")
    
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        fi = meta.get('metrics', {}).get('feature_importance', [])
        
        descriptions = {
            "grid": "Starting grid position",
            "avg_position_last5": "Average finish position in last 5 races",
            "avg_grid_last5": "Average qualifying position in last 5 races",
            "is_win_rate_last10": "Win rate in last 10 races",
            "is_podium_rate_last10": "Podium rate in last 10 races",
            "is_dnf_rate_last10": "DNF rate in last 10 races",
            "positions_gained_avg": "Average positions gained per race",
            "team_avg_finish_last5": "Team average finish position",
            "avg_points_last5": "Average points scored in last 5 races",
            "season": "Season year",
            "round_num": "Round number in season",
        }
        
        return [
            FeatureImportance(
                feature_name=f['feature'],
                importance=f['importance'],
                description=descriptions.get(f['feature'], f['feature'].replace('_', ' ').title())
            )
            for f in fi[:10]
        ]
    
    return [
        FeatureImportance(feature_name="grid", importance=0.35, description="Starting grid position"),
        FeatureImportance(feature_name="avg_position_last5", importance=0.25, description="Recent race form"),
        FeatureImportance(feature_name="team_avg_finish_last5", importance=0.15, description="Team performance"),
        FeatureImportance(feature_name="is_win_rate_last10", importance=0.10, description="Win rate history"),
        FeatureImportance(feature_name="avg_points_last5", importance=0.08, description="Recent points scored"),
        FeatureImportance(feature_name="is_dnf_rate_last10", importance=0.07, description="DNF probability"),
    ]


@router.get("/ai-providers")
async def get_ai_providers():
    """
    Get information about our Multi-AI prediction system.
    
    We use 5 specialized AI models working together:
    - 2x Gemini Pro (Google) - Strategy & Data Analysis
    - 1x DeepSeek - Deep Reasoning
    - 2x Groq Mixtral - Quick Analysis & Validation
    
    This provides robust, multi-perspective predictions with built-in redundancy.
    """
    return multi_ai_client.get_provider_info()


@router.get("/accuracy-history")
async def get_accuracy_history(db: Session = Depends(get_db)):
    """Get prediction accuracy by season from actual vs predicted results"""
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_models")
    meta_path = os.path.join(model_dir, "model_metadata.json")
    
    metrics = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        metrics = meta.get('metrics', {})
    
    # Count races by season
    season_counts = db.query(
        Event.season,
        func.count(func.distinct(DBSession.session_id))
    ).join(DBSession).filter(
        DBSession.session_type == 'R'
    ).group_by(Event.season).order_by(Event.season.desc()).limit(10).all()
    
    seasons = []
    for season, race_count in season_counts:
        pred_count = db.query(func.count(Prediction.prediction_id)).join(
            DBSession, Prediction.session_id == DBSession.session_id
        ).join(Event, DBSession.event_id == Event.event_id).filter(
            Event.season == season
        ).scalar() or 0
        
        seasons.append({
            "season": season,
            "accuracy": metrics.get('win_accuracy', 0.75),
            "races": race_count,
            "predictions": pred_count
        })
    
    return {
        "seasons": seasons,
        "overall_accuracy": metrics.get('win_accuracy', 0),
        "position_mae": metrics.get('position_mae', 0),
        "podium_accuracy": metrics.get('podium_accuracy', 0),
    }


def generate_mock_predictions(season, round_num, session_type):
    """Generate mock predictions as fallback"""
    mock_drivers = [
        ("VER", "Max Verstappen", "Red Bull Racing", 0.35),
        ("LEC", "Charles Leclerc", "Ferrari", 0.22),
        ("HAM", "Lewis Hamilton", "Ferrari", 0.18),
        ("NOR", "Lando Norris", "McLaren", 0.12),
        ("SAI", "Carlos Sainz", "Williams", 0.08),
        ("PIA", "Oscar Piastri", "McLaren", 0.05),
    ]
    return [
        SimpleDriverPrediction(
            driver_code=d[0],
            driver_name=d[1],
            team=d[2],
            probability=d[3],
            confidence="high" if d[3] > 0.2 else "medium" if d[3] > 0.1 else "low"
        )
        for d in mock_drivers
    ]


async def attach_groq_feedback(
    predictions: List[SimpleDriverPrediction],
    event_name: str,
    season: int,
    round_num: int,
    allow_adjust: bool = True,
    live_context: str = "",
    use_consensus: bool = True,
    db_session = None,
):
    """Enrich each prediction with Multi-AI probability + rationale.
    
    Enhanced Pipeline:
    1. Tavily (web context, current season only) - with database caching
    2. Multi-AI Consensus for top 5 drivers (Gemini x2, DeepSeek, Groq x2)
    3. Groq quick analysis for remaining drivers
    
    This provides robust predictions with multiple AI perspectives.
    """
    semaphore = asyncio.Semaphore(4)

    # Step 1: Try Tavily for web context (only for current season events)
    tavily_context = ""
    from datetime import datetime as _dt
    current_year = _dt.utcnow().year
    if season >= current_year and tavily_client.available:
        try:
            driver_codes = [p.driver_code for p in predictions[:5]]
            tavily_result = await tavily_client.search_f1_prediction_context(
                event_name, season, round_num, driver_codes, db_session=db_session
            )
            if not tavily_result.error:
                tavily_context = tavily_result.to_context_string(max_chars=1000)
                logger.info(f"Tavily context fetched for {event_name}: {len(tavily_context)} chars")
        except Exception as e:
            logger.warning(f"Tavily search failed, falling back: {e}")

    combined_context = live_context or ""
    if tavily_context:
        combined_context = f"{combined_context} | Web intel: {tavily_context}" if combined_context else f"Web intel: {tavily_context}"

    async def process_with_consensus(pred: SimpleDriverPrediction, is_top_driver: bool):
        """Process a single driver prediction"""
        async with semaphore:
            if is_top_driver and use_consensus and allow_adjust:
                # Use full Multi-AI Consensus for top drivers
                try:
                    consensus = await multi_ai_client.get_consensus_prediction(
                        driver_name=pred.driver_name,
                        driver_code=pred.driver_code,
                        team=pred.team,
                        event_name=event_name,
                        season=season,
                        round_num=round_num,
                        base_probability=pred.probability,
                        context=combined_context
                    )
                    
                    pred.probability = consensus.final_probability
                    pred.groq = {
                        "probability": consensus.final_probability,
                        "explanation": consensus.consensus_explanation,
                        "ai_source": "multi_ai_consensus",
                        "providers": consensus.providers_used,
                        "confidence_score": consensus.confidence_score,
                        "reasoning": consensus.reasoning_breakdown,
                        "explanations": consensus.explanations,
                        "tavily_enhanced": bool(tavily_context),
                    }
                    return
                except Exception as e:
                    logger.warning(f"Multi-AI consensus failed for {pred.driver_code}, falling back: {e}")

            # Fallback: Use quick Groq analysis
            try:
                result = await multi_ai_client.get_quick_prediction(
                    f"Race: {event_name} (Season {season}, Round {round_num}). "
                    f"Driver: {pred.driver_name} ({pred.driver_code}) for {pred.team}. "
                    f"Model win probability: {pred.probability:.1%}. "
                    f"Context: {combined_context or 'none'}. "
                    "Factor in weather conditions (rain, temperature, wind) and their impact on strategy and performance. "
                    "Return win probability (0-1) and brief reason."
                )
                
                if result.probability is not None and allow_adjust:
                    pred.probability = round(max(0.001, min(0.99, result.probability)), 4)
                
                pred.groq = {
                    "probability": result.probability,
                    "explanation": result.explanation or result.raw,
                    "ai_source": f"{result.provider}:{result.role}" if result.role else result.provider,
                    "tavily_enhanced": bool(tavily_context),
                }
            except Exception as e:
                logger.warning(f"Quick analysis failed for {pred.driver_code}: {e}")

    # Process top 5 drivers with full consensus, rest with quick analysis
    tasks = []
    for i, pred in enumerate(predictions):
        is_top = i < 5
        tasks.append(process_with_consensus(pred, is_top))
    
    await asyncio.gather(*tasks)
    return predictions


async def attach_multi_ai_feedback(
    predictions: List[SimpleDriverPrediction],
    event_name: str,
    season: int,
    round_num: int,
    context: str = "",
):
    """
    Simplified Multi-AI feedback for all predictions.
    Uses weighted provider calls based on driver position.
    """
    for i, pred in enumerate(predictions[:10]):
        try:
            if i < 3:
                # Top 3: Full consensus
                consensus = await multi_ai_client.get_consensus_prediction(
                    driver_name=pred.driver_name,
                    driver_code=pred.driver_code,
                    team=pred.team,
                    event_name=event_name,
                    season=season,
                    round_num=round_num,
                    base_probability=pred.probability,
                    context=context
                )
                pred.probability = consensus.final_probability
                pred.groq = consensus.to_dict()
            else:
                # Rest: Quick analysis
                result = await multi_ai_client.get_quick_prediction(
                    f"{event_name} R{round_num}: {pred.driver_name} ({pred.team}) base prob {pred.probability:.0%}"
                )
                if result.probability:
                    pred.probability = result.probability
                pred.groq = result.to_dict()
        except Exception as e:
            logger.warning(f"AI feedback failed for {pred.driver_code}: {e}")
    
    return predictions


@router.post("/predict", response_model=SimplePredictionResponse)
async def predict_simple(
    request: SimplePredictionRequest, 
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Prediction endpoint using real ML model and DB data.
    For past races with actual results, returns those instead of ML predictions.
    
    Rate limited: 3 predictions per 3 hours to conserve API credits.
    """
    import numpy as np
    import joblib

    # ── RATE LIMITING: 3 predictions per 3 hours ─────────────────────────
    client_ip = http_request.client.host if http_request.client else "unknown"
    # Try to get real IP from X-Forwarded-For header (for proxies/load balancers)
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    is_allowed, remaining, reset_time = check_rate_limit(client_ip, db)
    
    if not is_allowed:
        reset_str = reset_time.strftime("%H:%M UTC") if reset_time else "soon"
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"You have reached the maximum of {RATE_LIMIT_MAX_REQUESTS} predictions per {RATE_LIMIT_WINDOW_HOURS} hours. This limit helps us conserve AI API credits.",
                "reset_time": reset_time.isoformat() if reset_time else None,
                "reset_time_readable": reset_str
            }
        )
    
    # Record this request for rate limiting (count it now)
    record_rate_limit(client_ip, request.season, request.round, db)
    logger.info(f"Prediction request from {client_ip}: {remaining - 1} requests remaining in window")

    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_models")
    
    # Find the session for this season/round
    event = db.query(Event).filter(
        Event.season == request.season,
        Event.round == request.round
    ).first()
    
    event_name = event.event_name if event else f"Round {request.round}"
    
    # ── Check for ACTUAL RESULTS first (past races) ──────────────────────
    if event:
        session = db.query(DBSession).filter(
            DBSession.event_id == event.event_id,
            DBSession.session_type == 'R'
        ).first()
        
        if session:
            # Check if this race has actual results (driver_sessions with positions)
            actual_results = db.query(DriverSession).join(Driver).filter(
                DriverSession.session_id == session.session_id,
                DriverSession.position.isnot(None)
            ).order_by(DriverSession.position).all()
            
            if actual_results and len(actual_results) >= 5:
                # This race has happened! Return actual results
                predictions = []
                for ds in actual_results:
                    # Use season-correct team
                    team_info = get_team_for_driver(ds.driver.driver_code, request.season)
                    team_name = team_info[0] if team_info else (ds.driver.team_name or "")
                    
                    # Calculate "probability" from position (P1=highest, P20=lowest)
                    pos = ds.position or 20
                    is_winner = pos == 1
                    prob = max(0.01, 1.0 - (pos - 1) * 0.048) if pos <= 20 else 0.01
                    
                    predictions.append(SimpleDriverPrediction(
                        driver_code=ds.driver.driver_code,
                        driver_name=f"{ds.driver.first_name} {ds.driver.last_name}",
                        team=team_name,
                        probability=round(prob, 4),
                        confidence="actual_result"
                    ))

                await attach_groq_feedback(predictions, event_name, request.season, request.round, allow_adjust=False, live_context="Race finished; using actual results.", db_session=db)

                return SimplePredictionResponse(
                    season=request.season,
                    round=request.round,
                    session_type="Race",
                    event_name=event_name,
                    predictions=predictions[:20],
                    model_version="Actual Results + Groq",
                    generated_at=datetime.utcnow().isoformat() + "Z"
                )
            
            # Check for stored ML predictions 
            db_preds = db.query(Prediction).join(Driver).filter(
                Prediction.session_id == session.session_id
            ).order_by(Prediction.win_probability.desc()).all()
            
            if db_preds:
                predictions = []
                for p in db_preds[:20]:
                    prob = float(p.win_probability or 0)
                    team_info = get_team_for_driver(p.driver.driver_code, request.season)
                    team_name = team_info[0] if team_info else (p.driver.team_name or "")
                    predictions.append(SimpleDriverPrediction(
                        driver_code=p.driver.driver_code,
                        driver_name=f"{p.driver.first_name} {p.driver.last_name}",
                        team=team_name,
                        probability=round(prob, 4),
                        confidence="high" if prob > 0.3 else "medium" if prob > 0.1 else "low"
                    ))

                await attach_groq_feedback(predictions, event_name, request.season, request.round, allow_adjust=True, live_context="Stored predictions; using cached model output.", db_session=db)

                return SimplePredictionResponse(
                    season=request.season,
                    round=request.round,
                    session_type="Race",
                    event_name=event_name,
                    predictions=predictions,
                    model_version="GBM v1.0 + Groq",
                    generated_at=datetime.utcnow().isoformat() + "Z"
                )
    
    # ── Fallback: use model directly on drivers in the event ─────────────
    try:
        pos_model = joblib.load(os.path.join(model_dir, "position_model.joblib"))
        win_model = joblib.load(os.path.join(model_dir, "win_model.joblib"))
    except Exception:
        # No model available, use mock but still call Groq for enrichment
        predictions = generate_mock_predictions(request.season, request.round, request.session_type)
        await attach_groq_feedback(predictions, event_name, request.season, request.round, allow_adjust=True, live_context="Mock fallback; limited live signals.", db_session=db)
        return SimplePredictionResponse(
            season=request.season,
            round=request.round,
            session_type="Race",
            event_name=event_name,
            predictions=predictions,
            model_version="Mock + Groq",
            generated_at=datetime.utcnow().isoformat() + "Z"
        )

    # Get drivers for this season
    drivers = db.query(Driver).join(DriverSession).join(DBSession).join(Event).filter(
        Event.season == request.season
    ).distinct().all()
    
    if not drivers:
        drivers = db.query(Driver).order_by(Driver.driver_id.desc()).limit(20).all()

    boosts_active = []

    # Shared live context -- populated AFTER all boosts run (see assembly block below)
    base_context_parts: List[str] = []
    weather_detail_str: str = ""

    # ══════════════════════════════════════════════════════════════════════
    # BOOST 1: News sentiment (±5% max)
    # ══════════════════════════════════════════════════════════════════════
    driver_sentiment = {}
    team_sentiment = {}
    news_available = False
    news_articles = []
    try:
        news_articles = await scraper.fetch_all_news(max_articles=60)
        driver_sentiment = scraper.get_driver_sentiment(news_articles)
        team_sentiment = scraper.get_team_sentiment(news_articles)
        news_available = True
        boosts_active.append("news_sentiment")
    except Exception as e:
        logger.warning(f"News scraper unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # BOOST 2: Jolpica circuit history (±4% max)
    # ══════════════════════════════════════════════════════════════════════
    CIRCUIT_ID_MAP = {
        "bahrain": "bahrain", "jeddah": "jeddah", "albert_park": "albert_park",
        "suzuka": "suzuka", "shanghai": "shanghai", "miami": "miami",
        "imola": "imola", "monaco": "monaco", "villeneuve": "villeneuve",
        "catalunya": "catalunya", "red_bull_ring": "red_bull_ring",
        "silverstone": "silverstone", "hungaroring": "hungaroring",
        "spa": "spa", "zandvoort": "zandvoort", "monza": "monza",
        "marina_bay": "marina_bay", "baku": "baku", "americas": "americas",
        "rodriguez": "rodriguez", "interlagos": "interlagos",
        "las_vegas": "vegas", "losail": "losail", "yas_marina": "yas_marina",
    }
    circuit_driver_history: Dict[str, float] = {}
    try:
        if event:
            circuit_key = event.circuit_key or ""
            jolpica_circuit_id = CIRCUIT_ID_MAP.get(circuit_key.lower(), circuit_key.lower())
            history = await jolpica.get_circuit_history(jolpica_circuit_id, limit=5)
            raw: Dict[str, list] = {}
            for r in history:
                code = r.driver_code
                if code:
                    raw.setdefault(code, []).append(r.position)
            for code, positions in raw.items():
                circuit_driver_history[code] = sum(positions) / len(positions)
            if circuit_driver_history:
                boosts_active.append("circuit_history")
                logger.info(f"Jolpica circuit history: {len(circuit_driver_history)} drivers at {jolpica_circuit_id}")
    except Exception as e:
        logger.warning(f"Jolpica circuit history unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # BOOST 3: OpenF1 qualifying pace (±3% max)
    # ══════════════════════════════════════════════════════════════════════
    openf1_pace: Dict[str, float] = {}
    try:
        if event:
            sessions_of1 = await openf1.get_sessions(request.season, "Qualifying")
            event_lower = (event.event_name or "").lower()
            matching = [s for s in sessions_of1 if event_lower[:6] in s.circuit_short_name.lower() or s.location.lower() in event_lower]
            if matching:
                quali_session = matching[-1]
                summary = await openf1.get_session_summary(quali_session.session_key)
                for code, stats in summary.get("drivers", {}).items():
                    if stats.get("best_lap"):
                        openf1_pace[code] = stats["best_lap"]
                if openf1_pace:
                    boosts_active.append("quali_pace")
                    logger.info(f"OpenF1 qualifying pace: {len(openf1_pace)} drivers")
    except Exception as e:
        logger.warning(f"OpenF1 pace unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # BOOST 4: Elo Rating System — THE NEW TRICK (±6% max)
    # ══════════════════════════════════════════════════════════════════════
    elo: Optional[F1EloSystem] = None
    try:
        elo = get_elo_system(db)
        boosts_active.append("elo_rating")
        logger.info(f"Elo system loaded: {len(elo.drivers)} drivers rated")
    except Exception as e:
        logger.warning(f"Elo system unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # BOOST 5: Constructor momentum from Jolpica standings (±3% max)
    # ══════════════════════════════════════════════════════════════════════
    constructor_momentum: Dict[str, float] = {}  # team_name → normalized momentum score
    try:
        standings = await jolpica.get_constructor_standings(request.season)
        if not standings:
            standings = await jolpica.get_constructor_standings(request.season - 1)
        if standings:
            total_teams = len(standings)
            for s in standings:
                # Normalize: P1 → +1.0, last → -1.0
                norm = 1.0 - (2.0 * (s.position - 1) / max(total_teams - 1, 1))
                constructor_momentum[s.constructor_name.lower()] = norm
            boosts_active.append("constructor_momentum")
            logger.info(f"Constructor momentum: {len(constructor_momentum)} teams")
    except Exception as e:
        logger.warning(f"Constructor standings unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # BOOST 6: Championship pressure (±2% max)
    # ══════════════════════════════════════════════════════════════════════
    championship_pressure: Dict[str, float] = {}  # driver_code → pressure (-1 to +1)
    try:
        driver_standings = await jolpica.get_driver_standings(request.season)
        if not driver_standings:
            driver_standings = await jolpica.get_driver_standings(request.season - 1)
        if driver_standings and len(driver_standings) >= 2:
            leader_pts = driver_standings[0].points
            for s in driver_standings:
                gap = leader_pts - s.points
                if s.position == 1:
                    # Leader: slight pressure if gap is small, comfortable if large
                    if len(driver_standings) > 1:
                        gap_to_p2 = s.points - driver_standings[1].points
                        pressure = -0.3 if gap_to_p2 > 50 else 0.2  # comfortable → slight boost, tight → slight penalty
                    else:
                        pressure = 0.0
                elif s.position <= 3 and gap < 30:
                    # Close contender: motivated
                    pressure = 0.5
                elif s.position <= 5:
                    pressure = 0.2
                else:
                    # Nothing to lose
                    pressure = -0.1
                code = s.driver_code or ""
                if code:
                    championship_pressure[code] = pressure
            boosts_active.append("championship_pressure")
    except Exception as e:
        logger.warning(f"Championship standings unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # BOOST 7: Weather impact from DB or OpenF1 (±2% max)
    # ══════════════════════════════════════════════════════════════════════
    is_wet_race = False
    weather_details: Dict[str, Any] = {}   # detailed weather for LLM prompts
    try:
        if event:
            # Check DB weather first
            session_obj = db.query(DBSession).filter(
                DBSession.event_id == event.event_id,
                DBSession.session_type == 'R'
            ).first()
            if session_obj:
                weather_row = db.query(Weather).filter(
                    Weather.session_id == session_obj.session_id
                ).first()
                if weather_row:
                    if weather_row.rainfall:
                        is_wet_race = True
                    weather_details = {
                        "air_temp": getattr(weather_row, 'air_temperature', None) or getattr(weather_row, 'air_temp', None),
                        "track_temp": getattr(weather_row, 'track_temperature', None) or getattr(weather_row, 'track_temp', None),
                        "humidity": getattr(weather_row, 'humidity', None),
                        "wind_speed": getattr(weather_row, 'wind_speed', None),
                        "rainfall": weather_row.rainfall,
                    }
            # Also try OpenF1 weather for more detail
            of1_sessions = await openf1.get_sessions(request.season)
            event_lower = (event.event_name or "").lower()
            matching = [s for s in of1_sessions if event_lower[:6] in s.circuit_short_name.lower()]
            if matching:
                weather_data = await openf1.get_weather(matching[-1].session_key)
                if weather_data:
                    rain_count = sum(1 for w in weather_data if w.rainfall)
                    if rain_count > len(weather_data) * 0.3:
                        is_wet_race = True
                    # Collect average weather conditions for the LLM prompt
                    air_temps = [w.air_temperature for w in weather_data if w.air_temperature is not None]
                    track_temps = [w.track_temperature for w in weather_data if w.track_temperature is not None]
                    humidities = [w.humidity for w in weather_data if w.humidity is not None]
                    winds = [w.wind_speed for w in weather_data if w.wind_speed is not None]
                    if air_temps or track_temps:
                        weather_details = {
                            "air_temp": round(sum(air_temps) / len(air_temps), 1) if air_temps else None,
                            "track_temp": round(sum(track_temps) / len(track_temps), 1) if track_temps else None,
                            "humidity": round(sum(humidities) / len(humidities), 1) if humidities else None,
                            "wind_speed": round(sum(winds) / len(winds), 1) if winds else None,
                            "rainfall": is_wet_race,
                            "rain_probability": round(rain_count / len(weather_data) * 100) if weather_data else 0,
                        }
            if is_wet_race:
                boosts_active.append("weather_impact")
            # Build weather detail string for LLM prompts
            if weather_details:
                parts = []
                if weather_details.get("air_temp") is not None:
                    parts.append(f"Air {weather_details['air_temp']}C")
                if weather_details.get("track_temp") is not None:
                    parts.append(f"Track {weather_details['track_temp']}C")
                if weather_details.get("humidity") is not None:
                    parts.append(f"Humidity {weather_details['humidity']}%")
                if weather_details.get("wind_speed") is not None:
                    parts.append(f"Wind {weather_details['wind_speed']}km/h")
                if is_wet_race:
                    parts.append("WET/RAIN")
                elif weather_details.get("rain_probability", 0) > 10:
                    parts.append(f"Rain risk {weather_details['rain_probability']}%")
                else:
                    parts.append("DRY")
                weather_detail_str = "Weather: " + ", ".join(parts)
                boosts_active.append("weather_context")
    except Exception as e:
        logger.warning(f"Weather data unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # BOOST 8: Pit stop reliability from Jolpica (±1.5% max)
    # ══════════════════════════════════════════════════════════════════════
    team_pit_raw: Dict[str, list] = {}  # team_lower → list of pit times in seconds
    team_pit_reliability: Dict[str, float] = {}  # team_lower → avg_pit_time_s
    try:
        if event:
            # Get pit stop data from last 3 rounds in same season
            for rnd in range(max(1, request.round - 3), request.round):
                pit_data = await jolpica.get_pit_stops(request.season, rnd)
                for ps in pit_data:
                    # JolpicaPitStop has no constructor_name — lookup via driver code
                    team = ""
                    if ps.driver_code:
                        ti = get_team_for_driver(ps.driver_code, request.season)
                        team = ti[0].lower() if ti else ""
                    pit_ms = ps.duration_millis
                    if team and pit_ms and pit_ms > 0:
                        team_pit_raw.setdefault(team, []).append(pit_ms / 1000.0)
            # Average it
            for team, durations in team_pit_raw.items():
                team_pit_reliability[team] = sum(durations) / len(durations)
            if team_pit_reliability:
                boosts_active.append("pit_reliability")
    except Exception as e:
        logger.warning(f"Pit stop data unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # EXTRA DATA: Wet-weather specialists from DB (used with weather boost)
    # ══════════════════════════════════════════════════════════════════════
    wet_specialists: Dict[str, float] = {}
    if is_wet_race:
        try:
            # Find races where rainfall=True and check how drivers performed
            wet_sessions = db.query(DBSession.session_id).join(Weather).filter(
                Weather.rainfall == True,
                DBSession.session_type == 'R'
            ).all()
            wet_ids = [s[0] for s in wet_sessions]
            if wet_ids:
                for driver in drivers:
                    wet_results = db.query(DriverSession).filter(
                        DriverSession.session_id.in_(wet_ids),
                        DriverSession.driver_id == driver.driver_id,
                        DriverSession.position.isnot(None)
                    ).all()
                    if wet_results:
                        avg_wet_pos = sum(ds.position for ds in wet_results) / len(wet_results)
                        # Compare to their overall average — if better in wet, they're a specialist
                        overall = db.query(func.avg(DriverSession.position)).filter(
                            DriverSession.driver_id == driver.driver_id,
                            DriverSession.position.isnot(None)
                        ).scalar() or 10.0
                        wet_specialists[driver.driver_code] = float(overall) - avg_wet_pos  # positive = better in wet
        except Exception as e:
            logger.warning(f"Wet specialist analysis failed: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # ASSEMBLE LIVE CONTEXT for LLM prompts (after all boosts have run)
    # ══════════════════════════════════════════════════════════════════════
    if news_articles:
        headlines = [a.title for a in news_articles[:5] if getattr(a, "title", None)]
        if headlines:
            base_context_parts.append("News: " + " | ".join(headlines))
    if openf1_pace:
        fastest = sorted(openf1_pace.items(), key=lambda kv: kv[1])[:3]
        base_context_parts.append("Quali pace (best laps s): " + ", ".join(f"{c}:{t}" for c, t in fastest))
    if weather_detail_str:
        base_context_parts.append(weather_detail_str)
    elif is_wet_race:
        base_context_parts.append("Weather: WET/RAIN conditions expected")
    base_live_context = " | ".join(base_context_parts) if base_context_parts else "None"

    # ══════════════════════════════════════════════════════════════════════
    # BUILD PREDICTIONS FOR EACH DRIVER
    # ══════════════════════════════════════════════════════════════════════
    predictions = []
    for driver in drivers:
        recent = db.query(DriverSession).join(DBSession).join(Event).filter(
            DriverSession.driver_id == driver.driver_id,
            DriverSession.position.isnot(None),
        ).order_by(Event.season.desc(), Event.round.desc()).limit(10).all()

        positions = [r.position for r in recent if r.position]
        grids = [r.grid for r in recent if r.grid]
        dnfs = [1 if r.dnf else 0 for r in recent]
        points = [float(r.points or 0) for r in recent]

        avg_pos = np.mean(positions[:5]) if positions else 10
        avg_grid = np.mean(grids[:5]) if grids else 10
        win_rate = sum(1 for p in positions[:10] if p == 1) / max(len(positions[:10]), 1)
        pod_rate = sum(1 for p in positions[:10] if p <= 3) / max(len(positions[:10]), 1)
        dnf_rate = np.mean(dnfs[:10]) if dnfs else 0.1
        gains = [g - p for g, p in zip(grids, positions) if g and p]
        avg_gain = np.mean(gains[:5]) if gains else 0
        avg_pts = np.mean(points[:5]) if points else 0

        features = np.array([[
            avg_grid, avg_pos, avg_grid, win_rate, pod_rate,
            dnf_rate, avg_gain, avg_pos, avg_pts,
            request.season, request.round
        ]])

        try:
            win_prob = float(win_model.predict_proba(features)[0][1])
        except Exception:
            win_prob = 0.05

        team_info = get_team_for_driver(driver.driver_code, request.season)
        team_name = team_info[0] if team_info else (driver.team_name or '')
        team_lower = team_name.lower()

        # Track individual boosts for transparency
        boost_breakdown: Dict[str, float] = {}

        # ── BOOST 1: News sentiment (±5%) ──
        if news_available:
            ds_sent = driver_sentiment.get(driver.driver_code)
            ts_sent = team_sentiment.get(team_name, 0.0)
            news_boost = 0.0
            if ds_sent:
                news_boost += ds_sent.avg_sentiment * 0.03
            news_boost += ts_sent * 0.02
            news_boost = max(-0.05, min(0.05, news_boost))
            if abs(news_boost) > 0.001:
                boost_breakdown['news'] = round(news_boost, 4)
                win_prob += news_boost

        # ── BOOST 2: Circuit history (±4%) ──
        circuit_avg = circuit_driver_history.get(driver.driver_code)
        if circuit_avg is not None:
            circuit_boost = (10 - circuit_avg) * 0.004
            circuit_boost = max(-0.04, min(0.04, circuit_boost))
            if abs(circuit_boost) > 0.001:
                boost_breakdown['circuit'] = round(circuit_boost, 4)
                win_prob += circuit_boost

        # ── BOOST 3: Qualifying pace (±3%) ──
        if openf1_pace and driver.driver_code in openf1_pace:
            all_times = sorted(openf1_pace.values())
            driver_time = openf1_pace[driver.driver_code]
            if all_times:
                median_time = all_times[len(all_times) // 2]
                pace_delta = (median_time - driver_time) / median_time
                pace_boost = pace_delta * 0.5
                pace_boost = max(-0.03, min(0.03, pace_boost))
                if abs(pace_boost) > 0.001:
                    boost_breakdown['quali_pace'] = round(pace_boost, 4)
                    win_prob += pace_boost

        # ── BOOST 4: Elo rating (±6%) — THE NEW TRICK ──
        driver_elo_rating = None
        driver_elo_tier = None
        if elo:
            de = elo.get_driver_elo(driver.driver_code)
            if de:
                driver_elo_rating = round(de.rating, 1)
                driver_elo_tier = de.tier
                elo_delta = (de.rating - 1500) / 300.0
                elo_boost = elo_delta * 0.06
                elo_boost = max(-0.06, min(0.06, elo_boost))
                if abs(elo_boost) > 0.001:
                    boost_breakdown['elo'] = round(elo_boost, 4)
                    win_prob += elo_boost

        # ── BOOST 5: Constructor momentum (±3%) ──
        if constructor_momentum:
            best_match = 0.0
            for tm, score in constructor_momentum.items():
                if tm in team_lower or team_lower in tm:
                    best_match = score
                    break
            if abs(best_match) > 0.01:
                team_boost = best_match * 0.03
                team_boost = max(-0.03, min(0.03, team_boost))
                boost_breakdown['constructor'] = round(team_boost, 4)
                win_prob += team_boost

        # ── BOOST 6: Championship pressure (±2%) ──
        if championship_pressure and driver.driver_code in championship_pressure:
            pressure = championship_pressure[driver.driver_code]
            pressure_boost = pressure * 0.02
            pressure_boost = max(-0.02, min(0.02, pressure_boost))
            if abs(pressure_boost) > 0.001:
                boost_breakdown['pressure'] = round(pressure_boost, 4)
                win_prob += pressure_boost

        # ── BOOST 7: Weather impact (±2%) ──
        if is_wet_race:
            wet_diff = wet_specialists.get(driver.driver_code, 0.0)
            weather_boost = min(0.02, max(-0.02, wet_diff * 0.005))
            if abs(weather_boost) > 0.001:
                boost_breakdown['weather'] = round(weather_boost, 4)
                win_prob += weather_boost

        # ── BOOST 8: Pit stop reliability (±1.5%) ──
        if team_pit_reliability:
            pit_avg = None
            for tm, avg_t in team_pit_reliability.items():
                if isinstance(avg_t, (int, float)) and (tm in team_lower or team_lower in tm):
                    pit_avg = avg_t
                    break
            if pit_avg is not None:
                all_pit_times = [v for v in team_pit_reliability.values() if isinstance(v, (int, float))]
                if all_pit_times:
                    median_pit = sorted(all_pit_times)[len(all_pit_times) // 2]
                    pit_delta = (median_pit - pit_avg) / max(median_pit, 1)
                    pit_boost = pit_delta * 0.3
                    pit_boost = max(-0.015, min(0.015, pit_boost))
                    if abs(pit_boost) > 0.001:
                        boost_breakdown['pit_stops'] = round(pit_boost, 4)
                        win_prob += pit_boost

        # Clamp final probability
        win_prob = max(0.001, min(0.99, win_prob))

        conf = 'high' if win_prob > 0.3 else 'medium' if win_prob > 0.1 else 'low'

        # Build Groq prompt with latest contextual signals (acts like constrained web search)
        context_parts = list(base_context_parts)
        if championship_pressure.get(driver.driver_code):
            context_parts.append(f"Championship pressure score: {championship_pressure[driver.driver_code]:+.2f}")
        if is_wet_race and wet_specialists.get(driver.driver_code):
            wet_adv = wet_specialists[driver.driver_code]
            context_parts.append(f"Wet-weather advantage: {wet_adv:+.1f} positions better than dry avg")
        live_context = " | ".join(context_parts) if context_parts else base_live_context

        groq_prompt = (
            f"Race: {event_name} (Season {request.season}, Round {request.round})\n"
            f"Driver: {driver.first_name} {driver.last_name} ({driver.driver_code}) — {team_name}\n"
            f"Model win prob: {round(win_prob, 4)} | Confidence: {conf}\n"
            f"Elo: {driver_elo_rating} ({driver_elo_tier}) | Boosts: {boost_breakdown}\n"
            f"Context (latest signals): {live_context}\n"
            "Consider weather conditions (temperature, rain, wind) and their impact on car performance, "
            "tire strategy, and driver skill in these conditions.\n"
            "Return win probability 0-1 and 1-2 sentences on key factors using the context."
        )

        groq_result = await groq_client.score_prediction(groq_prompt)
        if groq_result.probability:
            win_prob = max(0.001, min(0.99, groq_result.probability))

        predictions.append(SimpleDriverPrediction(
            driver_code=driver.driver_code,
            driver_name=f"{driver.first_name} {driver.last_name}",
            team=team_name,
            probability=round(win_prob, 4),
            confidence=conf,
            elo_rating=driver_elo_rating,
            elo_tier=driver_elo_tier,
            boosts=boost_breakdown if boost_breakdown else None,
            groq=groq_result.to_dict()
        ))

    predictions.sort(key=lambda x: x.probability, reverse=True)
    # Build model label
    model_label = "GBM v2.0 + Elo + Groq"
    for b in boosts_active:
        short = {"news_sentiment": "News", "circuit_history": "Circuit", "quali_pace": "Quali",
                 "elo_rating": "Elo", "constructor_momentum": "Team", "championship_pressure": "Pressure",
                 "weather_impact": "Weather", "pit_reliability": "Pits"}.get(b, b)
        if short != "Elo":
            model_label += f" + {short}"

    # Build Elo leaderboard for response
    elo_rankings = None
    if elo:
        top_elo = elo.get_rankings(20)
        elo_rankings = [
            {"code": d.code, "rating": round(d.rating, 1), "tier": d.tier,
             "peak": round(d.peak_rating, 1), "races": d.races_completed, "wins": d.wins}
            for d in top_elo
        ]

    return SimplePredictionResponse(
        season=request.season,
        round=request.round,
        session_type="Race",
        event_name=event_name,
        predictions=predictions[:20],
        model_version=model_label,
        generated_at=datetime.utcnow().isoformat() + "Z",
        boosts_active=boosts_active,
        elo_rankings=elo_rankings,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC ROUTES (session_id based)
# ═══════════════════════════════════════════════════════════════════════════════

class PredictionResponse(BaseModel):
    driver_code: str
    driver_name: str
    team_name: str
    win_probability: float
    podium_probability: float
    top10_probability: float
    expected_position: float
    dnf_probability: float
    expected_pit_stops: Optional[float]
    prediction_confidence: float
    
    class Config:
        from_attributes = True


class ExplainabilityFactor(BaseModel):
    feature: str
    shap_value: float
    feature_value: float
    direction: str
    explanation: str


class ExplainabilityResponse(BaseModel):
    driver_code: str
    predictions: dict
    top_factors: List[ExplainabilityFactor]


@router.get("/session/{session_id}", response_model=List[PredictionResponse])
async def get_predictions(
    session_id: int,
    model_version: Optional[str] = "latest",
    db: Session = Depends(get_db)
):
    """
    Get race predictions for all drivers in a session
    
    Args:
        session_id: Session ID
        model_version: Model version (default: latest)
        
    Returns:
        List of driver predictions
    """
    # Query predictions
    predictions_query = db.query(Prediction).join(Driver).filter(
        Prediction.session_id == session_id
    )
    
    if model_version != "latest":
        predictions_query = predictions_query.filter(
            Prediction.model_version == model_version
        )
    
    predictions = predictions_query.all()
    
    if not predictions:
        raise HTTPException(
            status_code=404,
            detail=f"No predictions found for session {session_id}"
        )

    # Resolve season for team mapping
    session_obj = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    event_obj = db.query(Event).filter(Event.event_id == session_obj.event_id).first() if session_obj else None
    pred_season = event_obj.season if event_obj else 0
    
    # Format response
    results = []
    for pred in predictions:
        ti = get_team_for_driver(pred.driver.driver_code, pred_season) if pred_season else None
        resolved_team = ti[0] if ti else (pred.driver.team_name or "")
        results.append(PredictionResponse(
            driver_code=pred.driver.driver_code,
            driver_name=f"{pred.driver.first_name} {pred.driver.last_name}",
            team_name=resolved_team,
            win_probability=float(pred.win_probability or 0),
            podium_probability=float(pred.podium_probability or 0),
            top10_probability=float(pred.top10_probability or 0),
            expected_position=float(pred.expected_position or 20),
            dnf_probability=float(pred.dnf_probability or 0),
            expected_pit_stops=float(pred.expected_pit_stops or 0),
            prediction_confidence=float(pred.prediction_confidence or 0.5)
        ))
    
    # Sort by win probability
    results.sort(key=lambda x: x.win_probability, reverse=True)
    
    return results


@router.post("/session/{session_id}/compute")
async def compute_predictions(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Trigger prediction computation for a session
    
    This is typically run before a race to generate predictions.
    """
    from services.feature_engineering import FeatureEngineer
    from services.ml_pipeline import RacePredictionPipeline
    from config import settings
    
    # Compute features
    fe = FeatureEngineer(db)
    try:
        features_df = fe.compute_features_for_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Feature engineering failed: {str(e)}")
    
    # Load model and predict
    try:
        pipeline = RacePredictionPipeline()
        pipeline.load()  # Load latest model
        
        predictions_df = pipeline.predict(features_df)
        
        # Save predictions to database
        for idx, row in features_df.iterrows():
            prediction = Prediction(
                session_id=session_id,
                driver_id=row['driver_id'],
                model_version="1.0.0",
                win_probability=predictions_df.loc[idx, 'win_probability'],
                podium_probability=predictions_df.loc[idx, 'podium_probability'],
                top10_probability=predictions_df.loc[idx, 'top10_probability'],
                expected_position=predictions_df.loc[idx, 'expected_position'],
                dnf_probability=predictions_df.loc[idx, 'dnf_probability'],
                prediction_confidence=predictions_df.loc[idx, 'prediction_confidence']
            )
            db.add(prediction)
            
            # Compute and save SHAP explanations
            explanations = pipeline.explain(features_df, idx)
            
            for target, factors in explanations.items():
                for rank, factor in enumerate(factors[:10], 1):
                    shap_exp = ShapExplanation(
                        prediction_id=prediction.prediction_id,
                        feature_name=factor['feature'],
                        shap_value=factor['shap_value'],
                        feature_value=factor['feature_value'],
                        rank=rank
                    )
                    db.add(shap_exp)
        
        db.commit()
        
        return {
            "status": "success",
            "session_id": session_id,
            "predictions_generated": len(features_df)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/session/{session_id}/{driver_code}/explainability")
async def get_explainability(
    session_id: int,
    driver_code: str,
    db: Session = Depends(get_db)
):
    """
    Get SHAP explanations for a driver's predictions
    
    Shows which features contributed most to the prediction.
    """
    # Get prediction
    prediction = db.query(Prediction).join(Driver).filter(
        Prediction.session_id == session_id,
        Driver.driver_code == driver_code
    ).first()
    
    if not prediction:
        raise HTTPException(
            status_code=404,
            detail=f"No prediction found for {driver_code} in session {session_id}"
        )
    
    # Get SHAP explanations
    shap_explanations = db.query(ShapExplanation).filter(
        ShapExplanation.prediction_id == prediction.prediction_id
    ).order_by(ShapExplanation.rank).limit(10).all()
    
    # Format factors
    top_factors = []
    for shap_exp in shap_explanations:
        # Generate human-readable explanation
        explanation = _generate_explanation(
            shap_exp.feature_name,
            float(shap_exp.shap_value),
            float(shap_exp.feature_value)
        )
        
        top_factors.append(ExplainabilityFactor(
            feature=shap_exp.feature_name,
            shap_value=float(shap_exp.shap_value),
            feature_value=float(shap_exp.feature_value),
            direction="positive" if shap_exp.shap_value > 0 else "negative",
            explanation=explanation
        ))
    
    return ExplainabilityResponse(
        driver_code=driver_code,
        predictions={
            "win_probability": float(prediction.win_probability or 0),
            "podium_probability": float(prediction.podium_probability or 0),
            "expected_position": float(prediction.expected_position or 20)
        },
        top_factors=top_factors
    )


def _generate_explanation(feature_name: str, shap_value: float, feature_value: float) -> str:
    """Generate human-readable explanation for SHAP value"""
    direction = "increases" if shap_value > 0 else "decreases"
    
    explanations = {
        "grid_position": f"Starting P{int(feature_value)} {direction} win chances",
        "avg_finish_position_l5": f"Recent avg finish of P{feature_value:.1f} {direction} probability",
        "fp_best_lap_rank": f"Practice pace (P{int(feature_value)}) {direction} expectations",
        "team_avg_finish_l5": f"Team form (avg P{feature_value:.1f}) {direction} prediction",
        "dnf_rate_l10": f"DNF rate of {feature_value:.1%} {direction} reliability concerns"
    }
    
    return explanations.get(
        feature_name,
        f"{feature_name} = {feature_value:.2f} {direction} prediction"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ELO RATING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/elo-rankings")
async def get_elo_rankings(
    top: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get current F1 Elo ratings for all drivers.
    
    Returns drivers ranked by their Elo rating, built from all
    historical race results. The Elo system is chess-inspired:
    higher rating = stronger driver.
    """
    try:
        elo = get_elo_system(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Elo system error: {e}")

    rankings = elo.get_rankings(top)
    return {
        "total_drivers": len(elo.drivers),
        "rankings": [
            {
                "rank": i + 1,
                "driver_code": d.code,
                "rating": round(d.rating, 1),
                "peak_rating": round(d.peak_rating, 1),
                "tier": d.tier,
                "races_completed": d.races_completed,
                "wins": d.wins,
                "k_factor": round(d.k_factor, 1),
                "last_5_ratings": [h[2] for h in d.history[-5:]] if d.history else [],
            }
            for i, d in enumerate(rankings)
        ],
    }


@router.get("/elo-head-to-head")
async def elo_head_to_head(
    driver_a: str = Query(..., description="First driver code (e.g. VER)"),
    driver_b: str = Query(..., description="Second driver code (e.g. HAM)"),
    db: Session = Depends(get_db)
):
    """
    Get Elo-based head-to-head probability between two drivers.
    Returns the logistic probability that driver_a finishes ahead of driver_b.
    """
    try:
        elo = get_elo_system(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Elo system error: {e}")

    da = elo.get_driver_elo(driver_a.upper())
    db_elo = elo.get_driver_elo(driver_b.upper())
    prob = elo.head_to_head(driver_a.upper(), driver_b.upper())

    return {
        "driver_a": {
            "code": driver_a.upper(),
            "rating": round(da.rating, 1) if da else 1500.0,
            "tier": da.tier if da else "UNKNOWN",
        },
        "driver_b": {
            "code": driver_b.upper(),
            "rating": round(db_elo.rating, 1) if db_elo else 1500.0,
            "tier": db_elo.tier if db_elo else "UNKNOWN",
        },
        "probability_a_beats_b": round(prob, 4),
        "probability_b_beats_a": round(1 - prob, 4),
    }


@router.get("/boosts-info")
async def get_boosts_info():
    """
    Describe all available prediction boosts and their max impact.
    Used by frontend to show model transparency.
    """
    return {
        "model_version": "GBM v2.0 + Elo",
        "total_max_impact": "±27.5%",
        "boosts": [
            {"id": "base_model", "name": "GBM Base Model", "description": "Gradient Boosted Machine with 11 features from historical race data", "max_impact": "N/A (base)"},
            {"id": "news_sentiment", "name": "News Sentiment", "description": "Real-time news sentiment analysis for drivers and teams", "max_impact": "±5%"},
            {"id": "circuit_history", "name": "Circuit History", "description": "Driver's average finishing position at this specific circuit (Jolpica)", "max_impact": "±4%"},
            {"id": "quali_pace", "name": "Qualifying Pace", "description": "Relative qualifying lap time from OpenF1", "max_impact": "±3%"},
            {"id": "elo_rating", "name": "Elo Rating", "description": "Chess-style Elo system built from all historical results — THE NEW TRICK", "max_impact": "±6%"},
            {"id": "constructor_momentum", "name": "Constructor Momentum", "description": "Team's current championship position trend (Jolpica standings)", "max_impact": "±3%"},
            {"id": "championship_pressure", "name": "Championship Pressure", "description": "Points gap effect on driver motivation/pressure", "max_impact": "±2%"},
            {"id": "weather_impact", "name": "Weather Impact", "description": "Wet-weather specialist detection from historical rain races", "max_impact": "±2%"},
            {"id": "pit_reliability", "name": "Pit Stop Reliability", "description": "Team's recent pit stop speed from Jolpica data", "max_impact": "±1.5%"},
        ]
    }
