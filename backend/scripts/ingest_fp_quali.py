#!/usr/bin/env python3
"""
Ingest Practice (FP1/FP2/FP3) and Qualifying (Q/SQ) sessions from FastF1.
Re-uses existing events and drivers in the DB, only adds new sessions + laps.
"""
import os
import sys
import time
import traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import fastf1
import warnings
warnings.filterwarnings("ignore")

from database import engine, SessionLocal, Base
from models import (
    Event, Session as DBSessionModel, Driver, Constructor, DriverSession, Lap,
)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "fastf1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

SESSION_TYPES = ["FP1", "FP2", "FP3", "Q"]  # SQ is rare / not always available
INITIAL_DELAY = 4
MAX_RETRY_DELAY = 300

# Which seasons to ingest. Skip 2026 (no data yet).
SEASONS = list(range(2024, 2026))  # Start with recent seasons for speed


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)


def safe_api_call(func, *args, max_retries=6, **kwargs):
    delay = INITIAL_DELAY
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            time.sleep(INITIAL_DELAY)
            return result
        except Exception as e:
            err = str(e).lower()
            if "rate" in err or "limit" in err or "429" in err:
                wait = min(delay * (2 ** attempt), MAX_RETRY_DELAY)
                log(f"    Rate limited (attempt {attempt+1}), waiting {wait}s...")
                time.sleep(wait)
            elif "does not exist" in err or "no data" in err or "not available" in err:
                return None
            else:
                raise
    raise Exception(f"Max retries exceeded for {func.__name__}")


def ingest_session_type(db, year: int, round_num: int, event, stype: str):
    """Ingest a single session type (FP1/FP2/FP3/Q) for an event."""

    # Already exists?
    existing = db.query(DBSessionModel).filter(
        DBSessionModel.event_id == event.event_id,
        DBSessionModel.session_type == stype,
    ).first()
    if existing:
        # Check if we already have laps
        lap_count = (
            db.query(Lap)
            .join(DriverSession)
            .filter(DriverSession.session_id == existing.session_id)
            .count()
        )
        if lap_count > 0:
            log(f"      {stype} already has {lap_count} laps — skip")
            return 0
        else:
            session_obj = existing
    else:
        session_obj = None

    # Load from FastF1
    try:
        ff1 = safe_api_call(fastf1.get_session, year, round_num, stype)
        if ff1 is None:
            return 0
        safe_api_call(ff1.load, laps=True, telemetry=False, weather=False, messages=False)
    except Exception as e:
        err = str(e).lower()
        if "does not exist" in err or "no data" in err or "not available" in err:
            return 0
        log(f"      {stype} load error: {e}")
        return 0

    try:
        laps_df = ff1.laps
        if laps_df is None or laps_df.empty:
            log(f"      {stype}: no lap data")
            return 0
    except Exception:
        return 0

    # Create session if needed
    if not session_obj:
        total_laps = None
        try:
            total_laps = int(ff1.total_laps) if hasattr(ff1, "total_laps") and ff1.total_laps else None
        except Exception:
            pass

        session_obj = DBSessionModel(
            event_id=event.event_id,
            session_type=stype,
            session_date=event.event_date,
            total_laps=total_laps,
        )
        db.add(session_obj)
        db.flush()

    # Process results first — create DriverSession rows
    try:
        results = ff1.results
        if results is not None and not results.empty:
            for _, drv in results.iterrows():
                driver_code = str(drv.get("Abbreviation", ""))
                if not driver_code or driver_code == "nan":
                    continue

                driver = db.query(Driver).filter(Driver.driver_code == driver_code).first()
                if not driver:
                    first_name = str(drv.get("FirstName", ""))
                    last_name = str(drv.get("LastName", ""))
                    team_name = str(drv.get("TeamName", ""))
                    driver_num = None
                    try:
                        driver_num = int(drv.get("DriverNumber", 0)) or None
                    except Exception:
                        pass
                    driver = Driver(
                        driver_code=driver_code,
                        first_name=first_name if first_name != "nan" else "",
                        last_name=last_name if last_name != "nan" else "",
                        driver_number=driver_num,
                        team_name=team_name if team_name != "nan" else "",
                        nationality="",
                    )
                    db.add(driver)
                    db.flush()

                existing_ds = db.query(DriverSession).filter(
                    DriverSession.session_id == session_obj.session_id,
                    DriverSession.driver_id == driver.driver_id,
                ).first()
                if not existing_ds:
                    position = None
                    try:
                        p = drv.get("Position", None)
                        if p is not None and str(p) != "nan":
                            position = int(float(p))
                    except Exception:
                        pass
                    ds = DriverSession(
                        session_id=session_obj.session_id,
                        driver_id=driver.driver_id,
                        position=position,
                    )
                    db.add(ds)
            db.flush()
    except Exception as e:
        log(f"      {stype} results error: {e}")

    # Process laps
    laps_added = 0
    for _, lap in laps_df.iterrows():
        drv_code = str(lap.get("Driver", ""))
        try:
            lap_num = int(lap.get("LapNumber", 0))
        except (ValueError, TypeError):
            continue
        if not lap_num or lap_num < 1:
            continue

        drv = db.query(Driver).filter(Driver.driver_code == drv_code).first()
        if not drv:
            continue
        ds_obj = db.query(DriverSession).filter(
            DriverSession.session_id == session_obj.session_id,
            DriverSession.driver_id == drv.driver_id,
        ).first()
        if not ds_obj:
            # create on the fly for drivers only seen in laps
            ds_obj = DriverSession(
                session_id=session_obj.session_id,
                driver_id=drv.driver_id,
            )
            db.add(ds_obj)
            db.flush()

        existing_lap = db.query(Lap).filter(
            Lap.driver_session_id == ds_obj.driver_session_id,
            Lap.lap_number == lap_num,
        ).first()
        if existing_lap:
            continue

        lap_time = None
        try:
            lt = lap.get("LapTime", None)
            if lt is not None and hasattr(lt, "total_seconds"):
                lap_time = round(lt.total_seconds(), 3)
        except Exception:
            pass

        sector1 = sector2 = sector3 = None
        for attr, name in [("Sector1Time", "s1"), ("Sector2Time", "s2"), ("Sector3Time", "s3")]:
            try:
                s = lap.get(attr, None)
                if s is not None and hasattr(s, "total_seconds"):
                    val = round(s.total_seconds(), 3)
                    if name == "s1":
                        sector1 = val
                    elif name == "s2":
                        sector2 = val
                    else:
                        sector3 = val
            except Exception:
                pass

        compound = str(lap.get("Compound", "")) if str(lap.get("Compound", "")) != "nan" else None
        tyre_life = None
        try:
            tl = lap.get("TyreLife", None)
            if tl is not None and str(tl) != "nan":
                tyre_life = int(float(tl))
        except Exception:
            pass

        is_pit = False
        try:
            pit_in = lap.get("PitInTime", None)
            pit_out = lap.get("PitOutTime", None)
            is_pit = (pit_in is not None and str(pit_in) != "NaT") or (
                pit_out is not None and str(pit_out) != "NaT"
            )
        except Exception:
            pass

        position_val = None
        try:
            p = lap.get("Position", None)
            if p is not None and str(p) != "nan":
                position_val = int(float(p))
        except Exception:
            pass

        lap_obj = Lap(
            driver_session_id=ds_obj.driver_session_id,
            lap_number=lap_num,
            lap_time=lap_time,
            sector1_time=sector1,
            sector2_time=sector2,
            sector3_time=sector3,
            tyre_compound=compound,
            tyre_age=tyre_life,
            pit_in_lap=is_pit,
            position=position_val,
        )
        db.add(lap_obj)
        laps_added += 1

    db.commit()
    log(f"      {stype}: +{laps_added} laps")
    return laps_added


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    log("=" * 60)
    log("  FP / QUALIFYING SESSION INGESTION")
    log("=" * 60)

    total_laps = 0

    for year in SEASONS:
        log(f"\n  Season {year}")
        events = db.query(Event).filter(Event.season == year).order_by(Event.round).all()
        if not events:
            log(f"    No events in DB for {year}")
            continue

        for event in events:
            log(f"    R{event.round} {event.event_name}")
            for stype in SESSION_TYPES:
                try:
                    total_laps += ingest_session_type(db, year, event.round, event, stype)
                except Exception as e:
                    log(f"      {stype} FAILED: {e}")
                    traceback.print_exc()
                    db.rollback()

    # Stats
    from sqlalchemy import func as sqlfunc
    session_count = db.query(DBSessionModel).filter(
        DBSessionModel.session_type.in_(SESSION_TYPES)
    ).count()
    lap_count_total = (
        db.query(sqlfunc.count(Lap.lap_id))
        .join(DriverSession)
        .join(DBSessionModel)
        .filter(DBSessionModel.session_type.in_(SESSION_TYPES))
        .scalar()
    )

    log(f"\n  DONE — {session_count} FP/Q sessions, {lap_count_total} total FP/Q laps in DB")
    db.close()


if __name__ == "__main__":
    main()
