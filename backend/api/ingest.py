from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import logging
import traceback
from database import get_db
from database import SessionLocal
from models import IngestLog
from services.data_ingestion import DataIngestionService
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/ingest", tags=["ingest"])
logger = logging.getLogger(__name__)


# Live ingestion state (in-memory process state)
_live_task: Optional[asyncio.Task] = None
_live_state: Dict[str, Any] = {
    "running": False,
    "season": None,
    "interval_seconds": None,
    "started_at": None,
    "last_run_at": None,
    "last_success_at": None,
    "last_error": None,
    "runs": 0,
}


def _run_ingest_once_sync(season: int) -> Dict[str, int]:
    """Run one blocking ingest pass in a worker thread."""
    db = SessionLocal()
    log = IngestLog(
        status="running",
        source="fastf1-live",
        seasons_ingested=1,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        service = DataIngestionService(db)
        stats = service.ingest_season(season)

        log.status = "completed"
        log.completed_at = datetime.utcnow()
        log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
        log.events_ingested = int(stats.get("events", 0))
        log.sessions_ingested = int(stats.get("sessions", 0))
        log.drivers_ingested = int(stats.get("drivers", 0))
        db.commit()

        return {
            "events": int(stats.get("events", 0)),
            "sessions": int(stats.get("sessions", 0)),
            "drivers": int(stats.get("drivers", 0)),
        }
    except Exception as exc:
        db.rollback()
        try:
            log.status = "failed"
            log.completed_at = datetime.utcnow()
            log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
            log.error_message = str(exc)[:500]
            db.merge(log)
            db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()


async def _live_ingest_loop(season: int, interval_seconds: int):
    """Periodically ingest latest data for a season."""
    _live_state["running"] = True
    _live_state["season"] = season
    _live_state["interval_seconds"] = interval_seconds
    _live_state["started_at"] = datetime.utcnow().isoformat()
    _live_state["last_error"] = None

    while True:
        _live_state["last_run_at"] = datetime.utcnow().isoformat()
        try:
            await asyncio.to_thread(_run_ingest_once_sync, season)
            _live_state["runs"] += 1
            _live_state["last_success_at"] = datetime.utcnow().isoformat()
            _live_state["last_error"] = None
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Live ingestion iteration failed: %s", exc)
            _live_state["last_error"] = str(exc)
            _live_state["last_traceback"] = traceback.format_exc(limit=3)

        await asyncio.sleep(max(30, interval_seconds))


@router.post("/live/start")
async def start_live_ingest(
    season: int = Query(..., ge=1950, le=2100),
    interval_seconds: int = Query(default=300, ge=30, le=86400),
):
    """Start continuous ingestion loop for a season."""
    global _live_task

    if _live_task and not _live_task.done():
        return {
            "status": "already_running",
            "message": "Live ingestion is already running",
            "live": _live_state,
        }

    _live_state["running"] = True
    _live_state["season"] = season
    _live_state["interval_seconds"] = interval_seconds
    _live_state["started_at"] = datetime.utcnow().isoformat()
    _live_state["last_error"] = None

    _live_task = asyncio.create_task(_live_ingest_loop(season, interval_seconds))
    return {
        "status": "started",
        "message": f"Live ingestion started for season {season}",
        "live": _live_state,
    }


@router.post("/live/stop")
async def stop_live_ingest():
    """Stop continuous ingestion loop."""
    global _live_task

    if not _live_task or _live_task.done():
        _live_state["running"] = False
        return {
            "status": "not_running",
            "message": "Live ingestion is not running",
            "live": _live_state,
        }

    _live_task.cancel()
    try:
        await _live_task
    except asyncio.CancelledError:
        pass

    _live_state["running"] = False
    return {
        "status": "stopped",
        "message": "Live ingestion stopped",
        "live": _live_state,
    }


@router.get("/live/status")
async def live_ingest_status(db: Session = Depends(get_db)):
    """Get live ingestion runtime state and latest log entry."""
    latest = db.query(IngestLog).order_by(IngestLog.id.desc()).first()
    latest_log = latest.to_dict() if latest else None
    is_running = bool(_live_task and not _live_task.done())

    _live_state["running"] = is_running
    return {
        "live": _live_state,
        "latest_log": latest_log,
    }


@router.post("/run/season/{season}")
async def run_single_ingest(season: int):
    """Run one immediate ingest pass for a season."""
    if season < 1950 or season > 2100:
        raise HTTPException(status_code=400, detail="Invalid season")

    try:
        stats = await asyncio.to_thread(_run_ingest_once_sync, season)
        return {
            "status": "completed",
            "season": season,
            "stats": stats,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")

@router.get("/logs", response_model=List[dict])
async def get_ingest_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Get ingest history logs, most recent first"""
    logs = db.query(IngestLog).order_by(IngestLog.id.desc()).offset(skip).limit(limit).all()
    return [log.to_dict() for log in logs]

@router.get("/logs/{log_id}")
async def get_ingest_log(log_id: int, db: Session = Depends(get_db)):
    """Get a specific ingest log"""
    log = db.query(IngestLog).filter(IngestLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Ingest log not found")
    return log.to_dict()

@router.get("/status")
async def get_ingest_status(db: Session = Depends(get_db)):
    """Get current ingest status"""
    # Most recent log
    latest = db.query(IngestLog).order_by(IngestLog.id.desc()).first()
    
    if not latest:
        return {
            "status": "never_run",
            "message": "No ingestion has been run yet"
        }
    
    data = latest.to_dict()
    data["message"] = f"Last ingest: {latest.status} - {data['events_ingested']} events, {data['drivers_ingested']} drivers"
    
    return data

@router.post("/logs")
async def create_ingest_log(
    seasons: int = 0,
    events: int = 0,
    sessions: int = 0,
    drivers: int = 0,
    status: str = "running",
    db: Session = Depends(get_db)
):
    """Create a new ingest log entry"""
    log = IngestLog(
        seasons_ingested=seasons,
        events_ingested=events,
        sessions_ingested=sessions,
        drivers_ingested=drivers,
        status=status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log.to_dict()

@router.put("/logs/{log_id}")
async def update_ingest_log(
    log_id: int,
    status: str = None,
    error: str = None,
    seasons: int = None,
    events: int = None,
    sessions: int = None,
    drivers: int = None,
    db: Session = Depends(get_db)
):
    """Update an ingest log - for tracking ongoing ingestion"""
    log = db.query(IngestLog).filter(IngestLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Ingest log not found")
    
    if status:
        log.status = status
    if error:
        log.error_message = error
    if seasons is not None:
        log.seasons_ingested = seasons
    if events is not None:
        log.events_ingested = events
    if sessions is not None:
        log.sessions_ingested = sessions
    if drivers is not None:
        log.drivers_ingested = drivers
    
    # If completed, calculate duration
    if status == "completed" and log.completed_at is None:
        log.completed_at = datetime.utcnow()
        log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
    
    db.commit()
    db.refresh(log)
    return log.to_dict()

@router.delete("/logs/{log_id}")
async def delete_ingest_log(log_id: int, db: Session = Depends(get_db)):
    """Delete an ingest log - be careful!"""
    log = db.query(IngestLog).filter(IngestLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Ingest log not found")
    
    db.delete(log)
    db.commit()
    return {"message": "Ingest log deleted"}

@router.get("/summary")
async def get_ingest_summary(db: Session = Depends(get_db)):
    """Get summary statistics about all ingestion runs"""
    logs = db.query(IngestLog).all()
    
    if not logs:
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_events_ingested": 0,
            "total_drivers_ingested": 0,
            "total_sessions_ingested": 0,
            "last_run": None
        }
    
    successful = [l for l in logs if l.status == "completed"]
    failed = [l for l in logs if l.status == "failed"]
    
    return {
        "total_runs": len(logs),
        "successful_runs": len(successful),
        "failed_runs": len(failed),
        "total_events_ingested": sum(l.events_ingested for l in logs),
        "total_drivers_ingested": sum(l.drivers_ingested for l in logs),
        "total_sessions_ingested": sum(l.sessions_ingested for l in logs),
        "last_run": logs[-1].to_dict() if logs else None,
        "avg_duration_seconds": sum(l.duration_seconds for l in successful if l.duration_seconds) / len(successful) if successful else 0
    }
