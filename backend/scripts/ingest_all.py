#!/usr/bin/env python3
"""
F1 Data Ingestion - Robust Version
Ingests ALL F1 data from 2000-2025+ using FastF1.
Handles rate limits with exponential backoff.
Can resume from where it left off (idempotent).
"""
import os
import sys
import time
import json
import traceback
from datetime import datetime

import fastf1
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal, Base
from models import Event, Session, Driver, Constructor, DriverSession, Lap

# Config
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fastf1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

LOG_FILE = "/tmp/ingest_all.log"
INITIAL_DELAY = 5       # seconds between API calls
MAX_RETRY_DELAY = 300   # max 5 min wait on rate limit
SEASONS = list(range(2000, 2027))  # All F1 seasons 2000-2026


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")


def safe_api_call(func, *args, max_retries=10, **kwargs):
    """Call a FastF1 function with automatic rate-limit retry and exponential backoff."""
    delay = INITIAL_DELAY
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            time.sleep(INITIAL_DELAY)  # be nice between calls
            return result
        except Exception as e:
            err = str(e).lower()
            if 'rate' in err or 'limit' in err or '429' in err or 'ratelimit' in err:
                wait = min(delay * (2 ** attempt), MAX_RETRY_DELAY)
                log(f"    Rate limited (attempt {attempt+1}/{max_retries}), waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Max retries ({max_retries}) exceeded for {func.__name__}")


def get_existing_data(db):
    """Get a map of what we already have in the database."""
    existing = {}
    events = db.query(Event).all()
    for e in events:
        sessions = db.query(Session).filter(Session.event_id == e.event_id).all()
        race_sessions = [s for s in sessions if s.session_type == 'R']
        has_results = False
        has_laps = False
        if race_sessions:
            count = db.query(DriverSession).filter(
                DriverSession.session_id == race_sessions[0].session_id
            ).count()
            has_results = count > 0
            # Check if we have laps too
            if has_results:
                lap_count = db.query(Lap).join(DriverSession).filter(
                    DriverSession.session_id == race_sessions[0].session_id
                ).count()
                has_laps = lap_count > 0
        
        key = (e.season, e.round)
        existing[key] = {
            'event_id': e.event_id,
            'has_session': len(race_sessions) > 0,
            'has_results': has_results,
            'has_laps': has_laps,
        }
    return existing


def ingest_season(db, year, existing):
    """Ingest one season with all events/sessions/results."""
    log(f"\n{'='*60}")
    log(f"  SEASON {year}")
    log(f"{'='*60}")
    
    try:
        schedule = safe_api_call(fastf1.get_event_schedule, year, include_testing=False)
    except Exception as e:
        log(f"  Failed to get schedule for {year}: {e}")
        return 0, 0
    
    events_added = 0
    sessions_added = 0
    
    for _, row in schedule.iterrows():
        round_num = int(row.get('RoundNumber', 0))
        if round_num < 1:
            continue
        
        event_name = str(row.get('EventName', f'Round {round_num}'))
        country = str(row.get('Country', ''))
        location = str(row.get('Location', ''))
        
        # Parse date
        event_date = None
        for date_col in ['EventDate', 'Session5Date', 'Session1Date']:
            if date_col in row and row[date_col] is not None:
                try:
                    if hasattr(row[date_col], 'isoformat'):
                        event_date = row[date_col].to_pydatetime() if hasattr(row[date_col], 'to_pydatetime') else row[date_col]
                    break
                except Exception:
                    pass
        
        key = (year, round_num)
        
        # Create or get event
        event = db.query(Event).filter(Event.season == year, Event.round == round_num).first()
        if not event:
            event = Event(
                season=year,
                round=round_num,
                event_name=event_name,
                country=country,
                location=location,
                event_date=event_date,
                event_format=str(row.get('EventFormat', 'conventional')),
            )
            db.add(event)
            db.flush()
            events_added += 1
            log(f"  + Event: R{round_num} {event_name}")
        
        # Check if we already have complete data (results + laps) for this event
        if key in existing and existing[key]['has_results'] and existing[key]['has_laps']:
            log(f"  . R{round_num} {event_name} — already has results + laps, skipping")
            continue
        
        # 2026 events: schedule only, no race data
        if year >= 2026:
            continue
        
        # Load race session
        log(f"  > R{round_num}: {event_name} ...")
        try:
            ff1_session = safe_api_call(fastf1.get_session, year, round_num, 'R')
            safe_api_call(ff1_session.load, laps=True, telemetry=False, weather=False, messages=False)
        except Exception as e:
            err = str(e)
            if 'does not exist' in err or 'no data' in err.lower() or 'not available' in err.lower():
                log(f"    No race data available for {year} R{round_num}")
                continue
            log(f"    Error loading session: {e}")
            db.rollback()
            continue
        
        # Get or create race session in DB
        session_obj = db.query(Session).filter(
            Session.event_id == event.event_id,
            Session.session_type == 'R'
        ).first()
        
        if not session_obj:
            try:
                total_laps = int(ff1_session.total_laps) if hasattr(ff1_session, 'total_laps') and ff1_session.total_laps else None
            except Exception:
                total_laps = None
            
            session_obj = Session(
                event_id=event.event_id,
                session_type='R',
                session_date=event_date,
                total_laps=total_laps,
            )
            db.add(session_obj)
            db.flush()
            sessions_added += 1
        
        # Process results
        try:
            results = ff1_session.results
            if results is None or results.empty:
                log(f"    No results for R{round_num}")
                db.commit()
                continue
        except Exception:
            log(f"    Could not get results")
            db.commit()
            continue
        
        drivers_added_event = 0
        for _, drv in results.iterrows():
            driver_code = str(drv.get('Abbreviation', ''))
            if not driver_code or driver_code == 'nan':
                continue
            
            first_name = str(drv.get('FirstName', ''))
            last_name = str(drv.get('LastName', ''))
            driver_num = None
            try:
                driver_num = int(drv.get('DriverNumber', 0)) or None
            except (ValueError, TypeError):
                pass
            
            team_name = str(drv.get('TeamName', ''))
            team_color = str(drv.get('TeamColor', ''))
            
            # Get or create driver
            driver = db.query(Driver).filter(Driver.driver_code == driver_code).first()
            if not driver:
                driver = Driver(
                    driver_code=driver_code,
                    first_name=first_name if first_name != 'nan' else '',
                    last_name=last_name if last_name != 'nan' else '',
                    driver_number=driver_num,
                    team_name=team_name if team_name != 'nan' else '',
                    team_color=team_color if team_color != 'nan' else '',
                    nationality='',
                )
                db.add(driver)
                db.flush()
            else:
                # Update team info to latest
                if team_name and team_name != 'nan':
                    driver.team_name = team_name
                if team_color and team_color != 'nan':
                    driver.team_color = team_color
                if first_name and first_name != 'nan':
                    driver.first_name = first_name
                if last_name and last_name != 'nan':
                    driver.last_name = last_name
            
            # Get or create constructor
            constructor = None
            if team_name and team_name != 'nan':
                constructor = db.query(Constructor).filter(
                    Constructor.constructor_name == team_name
                ).first()
                if not constructor:
                    ckey = team_name.lower().replace(' ', '_').replace('-', '_')
                    constructor = Constructor(
                        constructor_key=ckey,
                        constructor_name=team_name,
                        nationality='',
                        team_color=team_color if team_color != 'nan' else '',
                    )
                    db.add(constructor)
                    db.flush()
                driver.constructor_id = constructor.constructor_id
            
            # Parse position
            position = None
            try:
                pos = drv.get('Position', None)
                if pos is not None and str(pos) != 'nan':
                    position = int(float(pos))
            except (ValueError, TypeError):
                pass
            
            grid = None
            try:
                g = drv.get('GridPosition', None)
                if g is not None and str(g) != 'nan':
                    grid = int(float(g))
            except (ValueError, TypeError):
                pass
            
            points = 0.0
            try:
                p = drv.get('Points', 0)
                if p is not None and str(p) != 'nan':
                    points = float(p)
            except (ValueError, TypeError):
                pass
            
            status = str(drv.get('Status', ''))
            is_dnf = status and status != 'nan' and 'Finished' not in status and '+' not in status
            
            # Check for existing driver_session
            existing_ds = db.query(DriverSession).filter(
                DriverSession.session_id == session_obj.session_id,
                DriverSession.driver_id == driver.driver_id
            ).first()
            
            if not existing_ds:
                ds = DriverSession(
                    session_id=session_obj.session_id,
                    driver_id=driver.driver_id,
                    position=position,
                    grid=grid,
                    points=points,
                    status=status if status != 'nan' else None,
                    dnf=is_dnf,
                )
                db.add(ds)
                drivers_added_event += 1
        
        db.flush()  # Ensure driver_session_ids are assigned before lap processing
        
        # Process laps
        try:
            laps_df = ff1_session.laps
            if laps_df is not None and not laps_df.empty:
                laps_added = 0
                for _, lap in laps_df.iterrows():
                    drv_code = str(lap.get('Driver', ''))
                    lap_num = None
                    try:
                        lap_num = int(lap.get('LapNumber', 0))
                    except (ValueError, TypeError):
                        continue
                    if not lap_num or lap_num < 1:
                        continue
                    
                    drv = db.query(Driver).filter(Driver.driver_code == drv_code).first()
                    if not drv:
                        continue
                    
                    # Get driver_session for this driver+session
                    ds_obj = db.query(DriverSession).filter(
                        DriverSession.session_id == session_obj.session_id,
                        DriverSession.driver_id == drv.driver_id
                    ).first()
                    if not ds_obj:
                        continue
                    
                    # Check if lap exists
                    existing_lap = db.query(Lap).filter(
                        Lap.driver_session_id == ds_obj.driver_session_id,
                        Lap.lap_number == lap_num
                    ).first()
                    if existing_lap:
                        continue
                    
                    lap_time_ms = None
                    try:
                        lt = lap.get('LapTime', None)
                        if lt is not None and hasattr(lt, 'total_seconds'):
                            lap_time_ms = int(lt.total_seconds() * 1000)
                    except Exception:
                        pass
                    
                    sector1 = None
                    try:
                        s = lap.get('Sector1Time', None)
                        if s is not None and hasattr(s, 'total_seconds'):
                            sector1 = round(s.total_seconds(), 3)
                    except Exception:
                        pass
                    
                    sector2 = None
                    try:
                        s = lap.get('Sector2Time', None)
                        if s is not None and hasattr(s, 'total_seconds'):
                            sector2 = round(s.total_seconds(), 3)
                    except Exception:
                        pass
                    
                    sector3 = None
                    try:
                        s = lap.get('Sector3Time', None)
                        if s is not None and hasattr(s, 'total_seconds'):
                            sector3 = round(s.total_seconds(), 3)
                    except Exception:
                        pass
                    
                    compound = str(lap.get('Compound', '')) if str(lap.get('Compound', '')) != 'nan' else None
                    tyre_life = None
                    try:
                        tl = lap.get('TyreLife', None)
                        if tl is not None and str(tl) != 'nan':
                            tyre_life = int(float(tl))
                    except Exception:
                        pass
                    
                    is_pit = False
                    try:
                        pit_in = lap.get('PitInTime', None)
                        pit_out = lap.get('PitOutTime', None)
                        is_pit = (pit_in is not None and str(pit_in) != 'NaT') or (pit_out is not None and str(pit_out) != 'NaT')
                    except Exception:
                        pass
                    
                    position_val = None
                    try:
                        p = lap.get('Position', None)
                        if p is not None and str(p) != 'nan':
                            position_val = int(float(p))
                    except Exception:
                        pass
                    
                    lap_obj = Lap(
                        driver_session_id=ds_obj.driver_session_id,
                        lap_number=lap_num,
                        lap_time=round(lap_time_ms / 1000.0, 3) if lap_time_ms else None,
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
                
                log(f"    ✓ {drivers_added_event} drivers, {laps_added} laps")
        except Exception as e:
            log(f"    ✓ {drivers_added_event} drivers (laps error: {e})")
        
        try:
            db.commit()
        except Exception as e:
            log(f"    Commit error: {e}")
            db.rollback()
    
    log(f"  Season {year}: +{events_added} events, +{sessions_added} sessions")
    return events_added, sessions_added


def main():
    log(f"\n{'#'*60}")
    log(f"  F1 COMPLETE DATA INGESTION")
    log(f"  Started: {datetime.now().isoformat()}")
    log(f"{'#'*60}")
    
    # Init DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        existing = get_existing_data(db)
        log(f"  Existing data: {len(existing)} events in database")
        
        total_events = 0
        total_sessions = 0
        
        for year in SEASONS:
            try:
                e, s = ingest_season(db, year, existing)
                total_events += e
                total_sessions += s
                # Refresh existing data after each season
                existing = get_existing_data(db)
            except Exception as ex:
                log(f"  SEASON {year} FAILED: {ex}")
                traceback.print_exc()
                db.rollback()
        
        # Final stats
        event_count = db.query(Event).count()
        session_count = db.query(Session).count()
        driver_count = db.query(Driver).count()
        ds_count = db.query(DriverSession).count()
        lap_count = db.query(Lap).count()
        
        log(f"\n{'#'*60}")
        log(f"  INGESTION COMPLETE")
        log(f"  Events: {event_count}")
        log(f"  Sessions: {session_count}")
        log(f"  Drivers: {driver_count}")
        log(f"  Driver-Sessions: {ds_count}")
        log(f"  Laps: {lap_count}")
        log(f"{'#'*60}")
        
    except Exception as e:
        log(f"FATAL: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    main()
