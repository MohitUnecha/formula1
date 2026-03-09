#!/usr/bin/env python3
"""
F1 Data Ingestion Script - FastF1 powered
Ingests all F1 data from 2000-2026 using the FastF1 library.
2026 gets schedule only (season not started).
2000-2025 get full results, drivers, constructors, standings.
"""
import sys
import os
import time
import warnings
from datetime import datetime, date
from decimal import Decimal

warnings.filterwarnings("ignore")

# Add parent dir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fastf1
import pandas as pd
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import text

from database import engine
from models import (
    Base, Event, Session, Driver, Constructor, DriverSession,
    Lap, PitStop, Weather, IngestLog
)

# Setup FastF1 cache
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fastf1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# ─── Team colors mapping ───────────────────────────────────────────
TEAM_COLORS = {
    'red bull': '#0600EF',
    'red bull racing': '#0600EF',
    'ferrari': '#DC0000',
    'scuderia ferrari': '#DC0000',
    'mercedes': '#00D2BE',
    'mclaren': '#FF8700',
    'aston martin': '#006F62',
    'alpine': '#0082FA',
    'alphatauri': '#2B4562',
    'rb': '#6692FF',
    'haas': '#FFFFFF',
    'haas f1 team': '#FFFFFF',
    'williams': '#005AFF',
    'sauber': '#52E252',
    'kick sauber': '#52E252',
    'alfa romeo': '#900000',
    'renault': '#FFF500',
    'racing point': '#F596C8',
    'force india': '#F596C8',
    'toro rosso': '#469BFF',
    'manor': '#ED1C24',
    'marussia': '#ED1C24',
    'caterham': '#006F42',
    'lotus': '#000000',
    'lotus f1': '#000000',
    'hrt': '#A09060',
    'virgin': '#CC0000',
    'toyota': '#CF1020',
    'brawn': '#D1FF00',
    'bmw sauber': '#006F62',
    'super aguri': '#D22730',
    'spyker': '#F5811F',
    'midland': '#F5811F',
    'jordan': '#F1DC00',
    'minardi': '#000000',
    'jaguar': '#005A2B',
    'bar': '#003399',
    'prost': '#0032A0',
    'arrows': '#FF8700',
    'benetton': '#00A550',
}

def get_team_color(team_name: str) -> str:
    if not team_name:
        return '#888888'
    name = team_name.lower().strip()
    for key, color in TEAM_COLORS.items():
        if key in name or name in key:
            return color
    return '#888888'


def safe_decimal(val, default=None):
    """Safely convert to Decimal"""
    if val is None or pd.isna(val):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=None):
    """Safely convert to int"""
    if val is None or pd.isna(val):
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def safe_str(val, default=''):
    """Safely convert to string"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val).strip()


def get_or_create_constructor(db: DBSession, team_name: str) -> Constructor:
    """Get or create a constructor by name"""
    if not team_name or pd.isna(team_name):
        team_name = 'Unknown'
    
    team_name = str(team_name).strip()
    key = team_name.lower().replace(' ', '_').replace('-', '_')
    
    existing = db.query(Constructor).filter_by(constructor_key=key).first()
    if existing:
        return existing
    
    constructor = Constructor(
        constructor_key=key,
        constructor_name=team_name,
        nationality='',
        team_color=get_team_color(team_name),
    )
    db.add(constructor)
    db.flush()
    return constructor


def get_or_create_driver(db: DBSession, code: str, first_name: str, last_name: str,
                          nationality: str, team_name: str, number: int = None) -> Driver:
    """Get or create a driver by code"""
    if not code or pd.isna(code):
        return None
    
    code = str(code).strip().upper()[:3]
    if not code:
        return None
    
    existing = db.query(Driver).filter_by(driver_code=code).first()
    if existing:
        # Update team info
        if team_name and not pd.isna(team_name):
            constructor = get_or_create_constructor(db, team_name)
            existing.constructor_id = constructor.constructor_id
            existing.team_name = str(team_name).strip()
            existing.team_color = get_team_color(str(team_name))
        if number and not pd.isna(number):
            existing.driver_number = safe_int(number)
        return existing
    
    constructor = get_or_create_constructor(db, team_name) if team_name else None
    
    driver = Driver(
        driver_code=code,
        driver_number=safe_int(number),
        first_name=safe_str(first_name),
        last_name=safe_str(last_name),
        nationality=safe_str(nationality),
        constructor_id=constructor.constructor_id if constructor else None,
        team_name=safe_str(team_name),
        team_color=get_team_color(safe_str(team_name)),
    )
    db.add(driver)
    db.flush()
    return driver


def timedelta_to_seconds(td):
    """Convert pandas Timedelta to seconds float"""
    if td is None or pd.isna(td):
        return None
    try:
        return td.total_seconds()
    except:
        return None


# ─── MAIN INGESTION ────────────────────────────────────────────────
def ingest_all():
    print("=" * 60)
    print("  F1 DATA INGESTION - FastF1 Powered")
    print("  Seasons: 2000-2026")
    print("=" * 60)
    
    db = DBSession(engine)
    start_time = time.time()
    
    total_events = 0
    total_sessions = 0
    total_drivers_added = 0
    
    try:
        # Phase 1: Ingest all seasons
        for year in range(2000, 2027):
            print(f"\n{'─' * 50}")
            print(f"  SEASON {year}")
            print(f"{'─' * 50}")
            
            try:
                schedule = fastf1.get_event_schedule(year, include_testing=False)
            except Exception as e:
                print(f"  ✗ Could not load schedule for {year}: {e}")
                continue
            
            if schedule is None or len(schedule) == 0:
                print(f"  ✗ No events found for {year}")
                continue
            
            events_added = 0
            
            for idx, row in schedule.iterrows():
                event_name = safe_str(row.get('EventName', row.get('OfficialEventName', f'Round {idx}')))
                
                # Skip testing events
                if 'test' in event_name.lower() or 'pre-season' in event_name.lower():
                    continue
                
                round_num = safe_int(row.get('RoundNumber', idx))
                if round_num is None or round_num < 1:
                    continue
                
                # Get date
                event_date_raw = row.get('EventDate', None)
                if event_date_raw is None:
                    event_date_raw = row.get('Session5Date', row.get('Session1Date', None))
                
                if event_date_raw is not None and not pd.isna(event_date_raw):
                    try:
                        event_date = pd.Timestamp(event_date_raw).date()
                    except:
                        event_date = date(year, 1, 1)
                else:
                    event_date = date(year, 1, 1)
                
                # Check for dupes
                existing = db.query(Event).filter_by(season=year, round=round_num).first()
                if existing:
                    continue
                
                event_format = safe_str(row.get('EventFormat', 'conventional'))
                country = safe_str(row.get('Country', ''))
                location = safe_str(row.get('Location', ''))
                circuit = safe_str(row.get('CircuitShortName', row.get('CircuitKey', '')))
                
                event = Event(
                    season=year,
                    round=round_num,
                    event_name=event_name,
                    event_date=event_date,
                    event_format=event_format,
                    country=country,
                    location=location,
                    circuit_key=circuit,
                )
                db.add(event)
                db.flush()
                events_added += 1
                
                # For 2026, skip session data (season hasn't started)
                if year >= 2026:
                    continue
                
                # ─── Load Race Session Results ───
                try:
                    race_session = fastf1.get_session(year, round_num, 'R')
                    # Only load weather for 2018+, laps for 2005+
                    load_weather = (year >= 2018)
                    load_laps = (year >= 2005)
                    race_session.load(telemetry=False, weather=load_weather, messages=False, laps=load_laps)
                    
                    # Create session record
                    try:
                        session_date = race_session.date
                    except Exception:
                        session_date = event_date
                    
                    try:
                        total_laps = safe_int(race_session.total_laps)
                    except Exception:
                        total_laps = None
                    
                    sess = Session(
                        event_id=event.event_id,
                        session_type='R',
                        session_date=session_date,
                        total_laps=total_laps,
                    )
                    db.add(sess)
                    db.flush()
                    total_sessions += 1
                    
                    # Get results
                    results = race_session.results
                    drivers_seen = set()  # Track drivers to avoid duplicates
                    if results is not None and len(results) > 0:
                        for _, r in results.iterrows():
                            driver_code = safe_str(r.get('Abbreviation', ''))
                            if not driver_code or driver_code in drivers_seen:
                                continue
                            drivers_seen.add(driver_code)
                            
                            first_name = safe_str(r.get('FirstName', ''))
                            last_name = safe_str(r.get('LastName', ''))
                            nationality = safe_str(r.get('CountryCode', ''))
                            team = safe_str(r.get('TeamName', ''))
                            number = safe_int(r.get('DriverNumber', None))
                            
                            driver = get_or_create_driver(db, driver_code, first_name, last_name, nationality, team, number)
                            if not driver:
                                continue
                            
                            position = safe_int(r.get('Position', None))
                            grid = safe_int(r.get('GridPosition', None))
                            points = safe_decimal(r.get('Points', 0))
                            status = safe_str(r.get('Status', 'Unknown'))
                            
                            is_dnf = status.lower() not in ['finished', '+1 lap', '+2 laps', '+3 laps', '+4 laps', '+5 laps', '']
                            if 'lap' in status.lower() and status.startswith('+'):
                                is_dnf = False
                            
                            ds = DriverSession(
                                session_id=sess.session_id,
                                driver_id=driver.driver_id,
                                position=position,
                                grid=grid,
                                points=points,
                                status=status,
                                dnf=is_dnf,
                                dnf_reason=status if is_dnf else None,
                            )
                            db.add(ds)
                            db.flush()
                            
                            # Ingest lap data
                            try:
                                laps_df = race_session.laps.pick_driver(driver_code)
                                if laps_df is not None and len(laps_df) > 0:
                                    for _, lap_row in laps_df.iterrows():
                                        lap_num = safe_int(lap_row.get('LapNumber'))
                                        if lap_num is None:
                                            continue
                                        
                                        lap = Lap(
                                            driver_session_id=ds.driver_session_id,
                                            lap_number=lap_num,
                                            lap_time=timedelta_to_seconds(lap_row.get('LapTime')),
                                            sector1_time=timedelta_to_seconds(lap_row.get('Sector1Time')),
                                            sector2_time=timedelta_to_seconds(lap_row.get('Sector2Time')),
                                            sector3_time=timedelta_to_seconds(lap_row.get('Sector3Time')),
                                            position=safe_int(lap_row.get('Position')),
                                            tyre_compound=safe_str(lap_row.get('Compound', '')),
                                            tyre_age=safe_int(lap_row.get('TyreLife')),
                                            is_personal_best=bool(lap_row.get('IsPersonalBest', False)) if not pd.isna(lap_row.get('IsPersonalBest', False)) else False,
                                            pit_out_lap=bool(lap_row.get('PitOutTime') is not None and not pd.isna(lap_row.get('PitOutTime'))),
                                            pit_in_lap=bool(lap_row.get('PitInTime') is not None and not pd.isna(lap_row.get('PitInTime'))),
                                            is_accurate=bool(lap_row.get('IsAccurate', True)) if not pd.isna(lap_row.get('IsAccurate', True)) else True,
                                        )
                                        db.add(lap)
                            except Exception as e:
                                pass  # Lap data not always available for older seasons
                    
                    # Weather data
                    try:
                        weather_df = race_session.weather_data
                        if weather_df is not None and len(weather_df) > 0:
                            # Sample every few rows to avoid too much data
                            sample_interval = max(1, len(weather_df) // 20)
                            for i in range(0, len(weather_df), sample_interval):
                                w_row = weather_df.iloc[i]
                                weather = Weather(
                                    session_id=sess.session_id,
                                    air_temp=safe_decimal(w_row.get('AirTemp')),
                                    track_temp=safe_decimal(w_row.get('TrackTemp')),
                                    humidity=safe_int(w_row.get('Humidity')),
                                    pressure=safe_decimal(w_row.get('Pressure')),
                                    wind_speed=safe_decimal(w_row.get('WindSpeed')),
                                    wind_direction=safe_int(w_row.get('WindDirection')),
                                    rainfall=bool(w_row.get('Rainfall', False)) if not pd.isna(w_row.get('Rainfall', False)) else False,
                                )
                                db.add(weather)
                    except Exception:
                        pass
                    
                    driver_count = db.query(DriverSession).filter_by(session_id=sess.session_id).count()
                    print(f"    R{round_num}: {event_name} → {driver_count} drivers")
                    
                except Exception as e:
                    db.rollback()
                    err_str = str(e)
                    if 'No data' in err_str or 'not available' in err_str.lower():
                        print(f"    R{round_num}: {event_name} → No race data available")
                    else:
                        print(f"    R{round_num}: {event_name} → Error: {err_str[:80]}")
                
                # Commit per event to avoid losing progress
                try:
                    db.commit()
                except Exception:
                    db.rollback()
            
            total_events += events_added
            print(f"  ✓ {year}: {events_added} events added")
            db.commit()
        
        # ─── Final stats ───
        elapsed = time.time() - start_time
        
        event_count = db.query(Event).count()
        session_count = db.query(Session).count()
        driver_count = db.query(Driver).count()
        constructor_count = db.query(Constructor).count()
        ds_count = db.query(DriverSession).count()
        lap_count = db.query(Lap).count()
        weather_count = db.query(Weather).count()
        
        # Log the ingestion
        log = IngestLog(
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=elapsed,
            status='completed',
            seasons_ingested=27,
            events_ingested=event_count,
            sessions_ingested=session_count,
            drivers_ingested=driver_count,
            source='fastf1',
        )
        db.add(log)
        db.commit()
        
        print(f"\n{'=' * 60}")
        print(f"  INGESTION COMPLETE")
        print(f"{'=' * 60}")
        print(f"  Time:          {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"  Events:        {event_count}")
        print(f"  Sessions:      {session_count}")
        print(f"  Drivers:       {driver_count}")
        print(f"  Constructors:  {constructor_count}")
        print(f"  Results:       {ds_count}")
        print(f"  Laps:          {lap_count}")
        print(f"  Weather:       {weather_count}")
        print(f"{'=' * 60}")
        
    except Exception as e:
        import traceback
        print(f"\n✗ FATAL ERROR: {e}")
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    ingest_all()
