"""
API Router: Live Race Predictions

WebSocket + REST endpoints for real-time prediction updates during live races.
Provides lap-by-lap win probability recalculation as the race unfolds.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import json
import logging
import numpy as np

from database import get_db
from models import Driver, DriverSession, Session as DBSession, Event, Lap
from team_mapping import get_team_for_driver

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Live state tracker ──────────────────────────────────────────────────────

class LiveRaceState:
    """Tracks live race state and connected WebSocket clients."""

    def __init__(self):
        self.active_sessions: Dict[int, dict] = {}  # session_id -> race state
        self.connections: List[WebSocket] = []
        self.is_live = False

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)


live_state = LiveRaceState()


# ─── Session timing (Practice / Qualifying) — 2026 only ─────────────────────

SESSION_TYPE_LABELS = {
    'FP1': 'Practice 1', 'FP2': 'Practice 2', 'FP3': 'Practice 3',
    'Q': 'Qualifying', 'SQ': 'Sprint Qualifying', 'S': 'Sprint', 'R': 'Race',
}

TIMING_SESSION_TYPES = {'FP1', 'FP2', 'FP3', 'Q', 'SQ'}


@router.get("/session/{session_id}/timing")
async def get_session_timing(
    session_id: int,
    up_to_lap: int = Query(default=None, ge=1, description="Show timing up to this lap number"),
    db: Session = Depends(get_db),
):
    """
    Live timing tower for Practice (FP1/FP2/FP3) and Qualifying sessions.
    Returns per-driver best times, sectors, and position order.
    """
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    event = db.query(Event).filter(Event.event_id == session.event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")

    session_type = session.session_type
    if session_type not in TIMING_SESSION_TYPES:
        raise HTTPException(400, f"Session type '{session_type}' is not a practice or qualifying session. Use /simulate for race sessions.")

    # Find max lap in this session
    max_lap = db.query(func.max(Lap.lap_number)).join(DriverSession).filter(
        DriverSession.session_id == session_id
    ).scalar() or 1

    cutoff = min(up_to_lap, max_lap) if up_to_lap else max_lap

    # All drivers in this session
    driver_sessions = (
        db.query(DriverSession)
        .join(Driver)
        .filter(DriverSession.session_id == session_id)
        .all()
    )

    if not driver_sessions:
        raise HTTPException(404, "No driver data for this session")

    timing_rows = []

    for ds in driver_sessions:
        driver = ds.driver

        # All laps up to cutoff
        laps = (
            db.query(Lap)
            .filter(
                Lap.driver_session_id == ds.driver_session_id,
                Lap.lap_number <= cutoff,
                Lap.lap_time.isnot(None),
                Lap.lap_time > 0,
            )
            .order_by(Lap.lap_number)
            .all()
        )

        if not laps:
            # Driver hasn't set a lap yet at this point — still include with no time
            timing_rows.append({
                "driver_code": driver.driver_code,
                "driver_name": f"{driver.first_name or ''} {driver.last_name or ''}".strip(),
                "team": driver.team_name or "",
                "position": None,
                "best_lap_time": None,
                "best_lap_time_fmt": "—",
                "best_s1": None, "best_s2": None, "best_s3": None,
                "best_s1_fmt": "—", "best_s2_fmt": "—", "best_s3_fmt": "—",
                "theoretical_best": None,
                "gap_to_leader": None,
                "laps_completed": 0,
                "current_tyre": None,
                "tyre_age": None,
                "last_lap_time": None,
                "last_lap_fmt": "—",
                "is_fastest": False,
                "in_q3": session_type in ('Q', 'SQ'),
            })
            continue

        # Filter hot laps (exclude very slow outlaps/in-laps) for qualifying
        # A hot lap is within 115% of the theoretical minimum for this session
        all_times = [float(l.lap_time) for l in laps if l.lap_time and float(l.lap_time) > 0]
        min_time = min(all_times) if all_times else None

        def _fmt_time(sec: float | None) -> str:
            if sec is None or sec <= 0:
                return "—"
            m = int(sec // 60)
            s = sec % 60
            return f"{m}:{s:06.3f}"

        hot_laps = [l for l in laps if l.lap_time and float(l.lap_time) < 300]
        best_lap = min(hot_laps, key=lambda l: float(l.lap_time)) if hot_laps else None

        # Per-sector bests
        s1_laps = [l for l in laps if l.sector1_time and float(l.sector1_time) > 0]
        s2_laps = [l for l in laps if l.sector2_time and float(l.sector2_time) > 0]
        s3_laps = [l for l in laps if l.sector3_time and float(l.sector3_time) > 0]

        best_s1 = float(min(s1_laps, key=lambda l: float(l.sector1_time)).sector1_time) if s1_laps else None
        best_s2 = float(min(s2_laps, key=lambda l: float(l.sector2_time)).sector2_time) if s2_laps else None
        best_s3 = float(min(s3_laps, key=lambda l: float(l.sector3_time)).sector3_time) if s3_laps else None

        theoretical_best = (
            round(best_s1 + best_s2 + best_s3, 3)
            if best_s1 and best_s2 and best_s3 else None
        )

        best_lap_time = float(best_lap.lap_time) if best_lap else None
        last_lap = laps[-1]
        last_lap_time = float(last_lap.lap_time) if last_lap.lap_time and float(last_lap.lap_time) < 300 else None

        team_info = get_team_for_driver(driver.driver_code, 2026)
        team_name = team_info[0] if team_info else (driver.team_name or "")

        timing_rows.append({
            "driver_code": driver.driver_code,
            "driver_name": f"{driver.first_name or ''} {driver.last_name or ''}".strip(),
            "team": team_name,
            "position": None,  # will fill after sorting
            "best_lap_time": best_lap_time,
            "best_lap_time_fmt": _fmt_time(best_lap_time),
            "best_s1": best_s1, "best_s2": best_s2, "best_s3": best_s3,
            "best_s1_fmt": _fmt_time(best_s1),
            "best_s2_fmt": _fmt_time(best_s2),
            "best_s3_fmt": _fmt_time(best_s3),
            "theoretical_best": theoretical_best,
            "theoretical_best_fmt": _fmt_time(theoretical_best),
            "gap_to_leader": None,  # fill below
            "laps_completed": len(laps),
            "current_tyre": last_lap.tyre_compound,
            "tyre_age": last_lap.tyre_age,
            "last_lap_time": last_lap_time,
            "last_lap_fmt": _fmt_time(last_lap_time),
            "is_fastest": False,
        })

    # Sort: drivers with a time ranked by best lap; no-time drivers at the bottom
    timed = sorted([r for r in timing_rows if r["best_lap_time"] is not None], key=lambda r: r["best_lap_time"])
    untimed = [r for r in timing_rows if r["best_lap_time"] is None]

    leader_time = timed[0]["best_lap_time"] if timed else None

    for i, row in enumerate(timed):
        row["position"] = i + 1
        row["gap_to_leader"] = round(row["best_lap_time"] - leader_time, 3) if i > 0 and leader_time else 0.0
        row["is_fastest"] = i == 0

    for i, row in enumerate(untimed):
        row["position"] = len(timed) + i + 1

    # Q1/Q2/Q3 cut lines for qualifying
    q_cutlines = {}
    if session_type in ('Q', 'SQ') and len(timed) >= 5:
        q_cutlines = {
            "q3_cut": min(10, len(timed)),   # top 10 to Q3
            "q2_cut": min(15, len(timed)),   # top 15 to Q2
        }

    all_rows = timed + untimed

    return {
        "session_id": session_id,
        "session_type": session_type,
        "session_label": SESSION_TYPE_LABELS.get(session_type, session_type),
        "event_name": event.event_name,
        "season": event.season,
        "round": event.round,
        "total_laps_in_session": max_lap,
        "displayed_up_to_lap": cutoff,
        "q_cutlines": q_cutlines,
        "timing": all_rows,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }




@router.get("/status")
async def get_live_status():
    """Check if a live race session is active."""
    return {
        "is_live": live_state.is_live,
        "active_sessions": list(live_state.active_sessions.keys()),
        "connected_clients": len(live_state.connections),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/simulate/{session_id}")
async def simulate_live_predictions(
    session_id: int,
    current_lap: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    """
    Simulate live predictions for a past race at a given lap.
    Uses only data available up to that lap to predict the outcome.
    """
    import joblib
    import os

    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    event = db.query(Event).filter(Event.event_id == session.event_id).first()
    season = event.season if event else 2026
    round_num = event.round if event else 1

    # Get total laps (Lap doesn't have session_id — join through DriverSession)
    total_laps = db.query(func.max(Lap.lap_number)).join(DriverSession).filter(
        DriverSession.session_id == session_id
    ).scalar() or 60

    # Get all drivers in this session
    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id,
        DriverSession.position.isnot(None),
    ).all()

    if not driver_sessions:
        raise HTTPException(404, "No driver data for this session")

    # Load ML model
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_models")
    try:
        win_model = joblib.load(os.path.join(model_dir, "win_model.joblib"))
    except Exception:
        win_model = None

    predictions = []
    race_progress = min(current_lap / total_laps, 1.0)

    for ds in driver_sessions:
        driver = ds.driver

        # Get laps up to current_lap for this driver
        laps = db.query(Lap).filter(
            Lap.driver_session_id == ds.driver_session_id,
            Lap.lap_number <= current_lap,
        ).order_by(Lap.lap_number).all()

        # Compute live features
        positions = [l.position for l in laps if l.position]
        lap_times = [float(l.lap_time) for l in laps if l.lap_time and float(l.lap_time) > 0 and float(l.lap_time) < 300]

        current_pos = positions[-1] if positions else (ds.grid or 10)
        avg_pos = np.mean(positions[-5:]) if positions else current_pos
        grid = ds.grid or 10
        positions_gained = grid - current_pos

        # Recent form from historical data
        recent = db.query(DriverSession).join(DBSession).join(Event).filter(
            DriverSession.driver_id == driver.driver_id,
            DriverSession.position.isnot(None),
            Event.season <= season,
        ).order_by(Event.season.desc(), Event.round.desc()).limit(10).all()

        hist_positions = [r.position for r in recent if r.position]
        win_rate = sum(1 for p in hist_positions[:10] if p == 1) / max(len(hist_positions[:10]), 1)
        pod_rate = sum(1 for p in hist_positions[:10] if p <= 3) / max(len(hist_positions[:10]), 1)
        dnf_rate = sum(1 for r in recent[:10] if r.dnf) / max(len(recent[:10]), 1)
        avg_hist = np.mean(hist_positions[:5]) if hist_positions else 10
        avg_pts = float(np.mean([float(r.points or 0) for r in recent[:5]])) if recent else 0.0

        # ML prediction (using model features)
        if win_model:
            try:
                features = np.array([[
                    grid, avg_pos, grid, win_rate, pod_rate,
                    dnf_rate, positions_gained, avg_hist, avg_pts,
                    season, round_num
                ]])
                base_prob = float(win_model.predict_proba(features)[0][1])
            except Exception:
                base_prob = 0.05
        else:
            # Heuristic based on current position
            base_prob = max(0.01, 1.0 - (current_pos - 1) * 0.048)

        # ── Live adjustment: weight current race state more as race progresses ──
        # Early race: mostly ML prediction
        # Late race: heavily weighted toward current position
        position_factor = max(0.01, 1.0 - (current_pos - 1) * 0.06)
        live_prob = base_prob * (1 - race_progress * 0.6) + position_factor * (race_progress * 0.6)
        live_prob = max(0.001, min(0.99, live_prob))

        # Pace adjustment: if driver has faster recent laps, boost them
        if len(lap_times) >= 3:
            recent_pace = np.mean(lap_times[-3:])
            all_driver_paces = []
            for other_ds in driver_sessions:
                other_laps = db.query(Lap).filter(
                    Lap.driver_session_id == other_ds.driver_session_id,
                    Lap.lap_number <= current_lap,
                    Lap.lap_time.isnot(None),
                    Lap.lap_time > 0,
                    Lap.lap_time < 300,
                ).order_by(Lap.lap_number.desc()).limit(3).all()
                if other_laps:
                    all_driver_paces.append(np.mean([float(l.lap_time) for l in other_laps]))

            if all_driver_paces:
                median_pace = np.median(all_driver_paces)
                pace_diff = (median_pace - recent_pace) / median_pace
                live_prob *= (1 + pace_diff * 2)
                live_prob = max(0.001, min(0.99, live_prob))

        team_info = get_team_for_driver(driver.driver_code, season)
        team_name = team_info[0] if team_info else (driver.team_name or "")

        # Tyre info from latest lap
        latest_lap = laps[-1] if laps else None
        tyre_compound = latest_lap.tyre_compound if latest_lap else None
        tyre_age = latest_lap.tyre_age if latest_lap else None

        predictions.append({
            "driver_code": driver.driver_code,
            "driver_name": f"{driver.first_name} {driver.last_name}",
            "team": team_name,
            "current_position": current_pos,
            "grid_position": grid,
            "positions_gained": positions_gained,
            "win_probability": round(live_prob, 4),
            "confidence": "high" if live_prob > 0.25 else "medium" if live_prob > 0.08 else "low",
            "tyre_compound": tyre_compound,
            "tyre_age": tyre_age,
            "avg_lap_time": round(np.mean(lap_times[-5:]), 3) if lap_times else None,
            "laps_completed": len(laps),
        })

    predictions.sort(key=lambda x: x["win_probability"], reverse=True)

    # Normalize probabilities to sum to 1
    total_prob = sum(p["win_probability"] for p in predictions)
    if total_prob > 0:
        for p in predictions:
            p["win_probability"] = round(p["win_probability"] / total_prob, 4)

    return {
        "session_id": session_id,
        "event_name": event.event_name if event else "",
        "season": season,
        "current_lap": current_lap,
        "total_laps": total_laps,
        "race_progress": round(race_progress * 100, 1),
        "predictions": predictions[:20],
        "model_version": "GBM Live v1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ─── WebSocket for streaming predictions ─────────────────────────────────────

@router.websocket("/ws")
async def live_predictions_ws(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for streaming live predictions.

    Client sends: {"action": "subscribe", "session_id": 123}
    Server streams: prediction updates every few seconds
    """
    await websocket.accept()
    live_state.connections.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(live_state.connections)}")

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "subscribe":
                session_id = data.get("session_id")
                current_lap = data.get("current_lap", 1)
                if session_id:
                    await websocket.send_json({
                        "type": "subscribed",
                        "session_id": session_id,
                        "message": f"Subscribed to live predictions for session {session_id}",
                    })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        live_state.connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining: {len(live_state.connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in live_state.connections:
            live_state.connections.remove(websocket)
