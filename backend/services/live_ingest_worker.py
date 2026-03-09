"""Dedicated live ingestion worker process.

Run as a separate process on Railway/Render worker service:
    python -m services.live_ingest_worker
"""

from __future__ import annotations

import os
import time
import logging
from datetime import datetime

from database import SessionLocal
from models import IngestLog
from services.data_ingestion import DataIngestionService

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("live_ingest_worker")


def _run_once(season: int) -> dict:
    db = SessionLocal()
    log = IngestLog(status="running", source="railway-worker", seasons_ingested=1)
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
        log.status = "failed"
        log.completed_at = datetime.utcnow()
        log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
        log.error_message = str(exc)
        db.commit()
        raise
    finally:
        db.close()


def _latest_season(default_season: int) -> int:
    db = SessionLocal()
    try:
        rows = db.execute("SELECT DISTINCT season FROM events ORDER BY season DESC LIMIT 1").fetchall()
        if rows:
            return int(rows[0][0])
    except Exception:
        pass
    finally:
        db.close()
    return default_season


def main() -> None:
    interval = int(os.getenv("LIVE_INGEST_INTERVAL_SECONDS", "120"))
    configured_season = int(os.getenv("LIVE_INGEST_SEASON", str(datetime.utcnow().year)))

    logger.info("Live ingest worker started (interval=%ss)", interval)

    while True:
        season = _latest_season(configured_season)
        try:
            stats = _run_once(season)
            logger.info("Ingest complete for season %s: %s", season, stats)
        except Exception as exc:
            logger.exception("Ingest iteration failed for season %s: %s", season, exc)

        time.sleep(max(30, interval))


if __name__ == "__main__":
    main()
