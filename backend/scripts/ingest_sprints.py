#!/usr/bin/env python3
"""
Sprint Session Ingestion
Finds all sprint-format events in the DB, downloads Sprint session data
from FastF1, and inserts Session/DriverSession/Lap records with session_type='S'.
"""
import os
import sys
import time
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

INITIAL_DELAY = 5
MAX_RETRY_DELAY = 300


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def safe_api_call(func, *args, max_retries=10, **kwargs):
    delay = INITIAL_DELAY
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            time.sleep(INITIAL_DELAY)
            return result
        except Exception as e:
            err = str(e).lower()
            if 'rate' in err or 'limit' in err or '429' in err or 'ratelimit' in err:
                wait = min(delay * (2 ** attempt), MAX_RETRY_DELAY)
                log(f"  Rate limited (attempt {attempt+1}/{max_retries}), waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Max retries ({max_retries}) exceeded")


def ingest_sprint_for_event(db, event):
    """Load sprint session for one event and insert results + laps."""
    year = event.season
    round_num = event.round
    
    # Check if sprint session already exists
    existing = db.query(Session).filter(
        Session.event_id == event.event_id,
        Session.session_type == 'S'
    ).first()
    
    if existing:
        # Check if it has results
        count = db.query(DriverSession).filter(
            DriverSession.session_id == existing.session_id
        ).count()
        if count > 0:
            log(f"  . R{round_num} {event.event_name} — sprint already has {count} drivers, skipping")
            return 0, 0
    
    log(f"  > R{round_num}: {event.event_name} (Sprint) ...")
    
    # Load sprint session from FastF1
    # Try different identifiers since FastF1 version differences
    ff1_session = None
    for identifier in ['Sprint', 'S']:
        try:
            ff1_session = safe_api_call(fastf1.get_session, year, round_num, identifier)
            safe_api_call(ff1_session.load, laps=True, telemetry=False, weather=False, messages=False)
            break
        except KeyError as e:
            # FastF1 crashes on some older sprint sessions (e.g. 2022) with KeyError: 'DriverNumber'
            log(f"    FastF1 KeyError loading sprint: {e} (data format issue, skipping)")
            ff1_session = None
            break
        except Exception as e:
            err = str(e).lower()
            if 'does not exist' in err or 'no data' in err or 'not available' in err or 'invalid' in err:
                continue
            raise
    
    if ff1_session is None:
        log(f"    No sprint data available for {year} R{round_num}")
        return 0, 0
    
    # Create session record
    session_obj = existing
    if not session_obj:
        total_laps = None
        try:
            total_laps = int(ff1_session.total_laps) if hasattr(ff1_session, 'total_laps') and ff1_session.total_laps else None
        except Exception:
            pass
        
        session_obj = Session(
            event_id=event.event_id,
            session_type='S',
            session_date=event.event_date,
            total_laps=total_laps,
        )
        db.add(session_obj)
        db.flush()
    
    # Process results
    try:
        results = ff1_session.results
        if results is None or results.empty:
            log(f"    No results for sprint R{round_num}")
            db.commit()
            return 1, 0
    except Exception:
        log(f"    Could not get results")
        db.commit()
        return 1, 0
    
    drivers_added = 0
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
        
        # Get or create constructor
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
        is_dnf = bool(status and status != 'nan' and 'Finished' not in status and '+' not in status)
        
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
            drivers_added += 1
    
    db.flush()
    
    # Process laps
    laps_added = 0
    try:
        laps_df = ff1_session.laps
        if laps_df is not None and not laps_df.empty:
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
                
                ds_obj = db.query(DriverSession).filter(
                    DriverSession.session_id == session_obj.session_id,
                    DriverSession.driver_id == drv.driver_id
                ).first()
                if not ds_obj:
                    continue
                
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
    except Exception as e:
        log(f"    Laps error: {e}")
    
    try:
        db.commit()
        log(f"    ✓ {drivers_added} drivers, {laps_added} laps")
    except Exception as e:
        log(f"    Commit error: {e}")
        db.rollback()
        return 0, 0
    
    return 1, drivers_added


def main():
    log("=" * 60)
    log("  SPRINT SESSION INGESTION")
    log("=" * 60)
    
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Find all sprint-format events
        sprint_events = db.query(Event).filter(
            Event.event_format.in_(['sprint', 'sprint_qualifying', 'sprint_shootout'])
        ).order_by(Event.season, Event.round).all()
        
        log(f"  Found {len(sprint_events)} sprint weekend events")
        
        # Also check for any events that might be sprint but we missed
        # Sprint weekends by year-round (F1 official):
        # 2021: Silverstone (R10), Monza (R14), Interlagos (R19)
        # 2022: Imola (R4), Austria (R11), Interlagos (R22)
        # 2023: Azerbaijan (R4), Austria (R10), Belgium (R12), Qatar (R17), COTA (R19), Brazil (R21)
        # 2024: China (R5), Miami (R6), Austria (R11), COTA (R19), Brazil (R21), Qatar (R23)
        # 2025: China, Miami, Belgium, COTA, Brazil, Qatar
        # 2026: TBD (projected same format as 2025)
        
        known_sprints = {
            2021: [10, 14, 19],
            2022: [4, 11, 22],
            2023: [4, 10, 12, 17, 19, 21],
            2024: [5, 6, 11, 19, 21, 23],
            2025: [3, 6, 13, 19, 21, 23],
            2026: [3, 6, 13, 19, 21, 23],  # Projected — update when confirmed
        }
        
        # Add any events from known_sprints that aren't already in sprint_events
        sprint_event_keys = {(e.season, e.round) for e in sprint_events}
        extra_events = []
        for year, rounds in known_sprints.items():
            for rnd in rounds:
                if (year, rnd) not in sprint_event_keys:
                    ev = db.query(Event).filter(Event.season == year, Event.round == rnd).first()
                    if ev:
                        extra_events.append(ev)
                        log(f"  + Adding unlabeled sprint event: {year} R{rnd} {ev.event_name}")
        
        all_sprint_events = sprint_events + extra_events
        all_sprint_events.sort(key=lambda e: (e.season, e.round))
        
        log(f"  Total sprint events to process: {len(all_sprint_events)}")
        
        total_sessions = 0
        total_drivers = 0
        
        for event in all_sprint_events:
            try:
                s, d = ingest_sprint_for_event(db, event)
                total_sessions += s
                total_drivers += d
            except Exception as e:
                log(f"    FAILED: {e}")
                traceback.print_exc()
                db.rollback()
        
        # Stats
        sprint_count = db.query(Session).filter(Session.session_type == 'S').count()
        sprint_ds = db.query(DriverSession).join(Session).filter(Session.session_type == 'S').count()
        sprint_laps = db.query(Lap).join(DriverSession).join(Session).filter(Session.session_type == 'S').count()
        
        log(f"\n{'='*60}")
        log(f"  SPRINT INGESTION COMPLETE")
        log(f"  Sprint sessions: {sprint_count}")
        log(f"  Sprint driver-sessions: {sprint_ds}")
        log(f"  Sprint laps: {sprint_laps}")
        log(f"{'='*60}")
        
    except Exception as e:
        log(f"FATAL: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    main()
