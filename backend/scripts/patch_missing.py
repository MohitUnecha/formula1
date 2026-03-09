#!/usr/bin/env python3
"""
F1 Data Patch Script - Fill missing seasons with rate limiting.
Only processes seasons/events not already in the database.
Adds 8-second delay between session loads to stay under API rate limits.
"""
import sys, os, time, warnings
from datetime import datetime, date
from decimal import Decimal
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fastf1
from sqlalchemy.orm import Session as DBSession

from database import engine
from models import Base, Event, Session, Driver, Constructor, DriverSession, Lap, Weather

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fastf1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

TEAM_COLORS = {
    'red bull': '#0600EF', 'red bull racing': '#0600EF', 'ferrari': '#DC0000',
    'scuderia ferrari': '#DC0000', 'mercedes': '#00D2BE', 'mclaren': '#FF8700',
    'aston martin': '#006F62', 'alpine': '#0082FA', 'alphatauri': '#2B4562',
    'rb': '#6692FF', 'haas': '#FFFFFF', 'haas f1 team': '#FFFFFF',
    'williams': '#005AFF', 'sauber': '#52E252', 'kick sauber': '#52E252',
    'alfa romeo': '#900000', 'renault': '#FFF500', 'racing point': '#F596C8',
    'force india': '#F596C8', 'toro rosso': '#469BFF', 'lotus': '#000000',
    'caterham': '#006F42', 'manor': '#ED1C24', 'marussia': '#ED1C24',
    'hrt': '#A09060', 'virgin': '#CC0000', 'toyota': '#CF1020', 'brawn': '#D1FF00',
    'bmw sauber': '#006F62', 'super aguri': '#D22730', 'spyker': '#F5811F',
    'jordan': '#F1DC00', 'minardi': '#000000', 'jaguar': '#005A2B',
    'bar': '#003399', 'benetton': '#00A550', 'arrows': '#FF8700', 'prost': '#0032A0',
}

def get_team_color(name):
    if not name: return '#888888'
    n = name.lower().strip()
    for k, v in TEAM_COLORS.items():
        if k in n or n in k: return v
    return '#888888'

def sf(v, d=None):
    if v is None or (isinstance(v, float) and pd.isna(v)): return d
    try: return float(v)
    except: return d

def si(v, d=None):
    if v is None or (isinstance(v, float) and pd.isna(v)): return d
    try: return int(v)
    except: return d

def ss(v, d=''):
    if v is None or (isinstance(v, float) and pd.isna(v)): return d
    return str(v).strip()

def td_sec(td):
    if td is None or pd.isna(td): return None
    try: return td.total_seconds()
    except: return None

def get_or_create_constructor(db, team_name):
    if not team_name or pd.isna(team_name): team_name = 'Unknown'
    team_name = str(team_name).strip()
    key = team_name.lower().replace(' ', '_').replace('-', '_')
    existing = db.query(Constructor).filter_by(constructor_key=key).first()
    if existing: return existing
    c = Constructor(constructor_key=key, constructor_name=team_name, nationality='', team_color=get_team_color(team_name))
    db.add(c); db.flush()
    return c

def get_or_create_driver(db, code, first, last, nat, team, num=None):
    if not code or pd.isna(code): return None
    code = str(code).strip().upper()[:3]
    if not code: return None
    existing = db.query(Driver).filter_by(driver_code=code).first()
    if existing:
        if team and not pd.isna(team):
            con = get_or_create_constructor(db, team)
            existing.constructor_id = con.constructor_id
            existing.team_name = str(team).strip()
            existing.team_color = get_team_color(str(team))
        if num and not pd.isna(num): existing.driver_number = si(num)
        return existing
    con = get_or_create_constructor(db, team) if team else None
    d = Driver(driver_code=code, driver_number=si(num), first_name=ss(first), last_name=ss(last),
               nationality=ss(nat), constructor_id=con.constructor_id if con else None,
               team_name=ss(team), team_color=get_team_color(ss(team)))
    db.add(d); db.flush()
    return d


def patch_missing():
    print("=" * 60)
    print("  F1 DATA PATCH - Fill Missing Seasons")
    print("  Rate-limited: 8s delay between loads")
    print("=" * 60)

    db = DBSession(engine)
    start = time.time()
    api_calls = 0

    try:
        for year in range(2000, 2026):
            # Check existing events
            existing_events = db.query(Event).filter(Event.season == year).count()
            existing_sessions = db.query(Session.session_id).join(Event).filter(Event.season == year).count()

            try:
                schedule = fastf1.get_event_schedule(year, include_testing=False)
            except Exception as e:
                print(f"  {year}: SKIP - {e}")
                continue

            expected = len([1 for _, r in schedule.iterrows()
                          if r.get('RoundNumber', 0) >= 1 and 'test' not in str(r.get('EventName', '')).lower()])

            if existing_events >= expected and existing_sessions >= expected:
                print(f"  {year}: COMPLETE ({existing_events} events, {existing_sessions} sessions)")
                continue

            print(f"\n{'─' * 50}")
            print(f"  SEASON {year} (have {existing_events}/{expected} events, {existing_sessions} sessions)")
            print(f"{'─' * 50}")

            for _, row in schedule.iterrows():
                event_name = ss(row.get('EventName', ''))
                if 'test' in event_name.lower() or 'pre-season' in event_name.lower():
                    continue
                round_num = si(row.get('RoundNumber', 0))
                if not round_num or round_num < 1:
                    continue

                # Check if event already exists
                existing_ev = db.query(Event).filter_by(season=year, round=round_num).first()
                if existing_ev:
                    # Check if session exists
                    existing_sess = db.query(Session).filter_by(event_id=existing_ev.event_id, session_type='R').first()
                    if existing_sess:
                        continue  # Already have this race
                    event = existing_ev
                else:
                    # Create event
                    event_date_raw = row.get('EventDate', None)
                    try:
                        event_date = pd.Timestamp(event_date_raw).date() if event_date_raw and not pd.isna(event_date_raw) else date(year, 1, 1)
                    except:
                        event_date = date(year, 1, 1)

                    event = Event(
                        season=year, round=round_num, event_name=event_name,
                        event_date=event_date,
                        event_format=ss(row.get('EventFormat', 'conventional')),
                        country=ss(row.get('Country', '')),
                        location=ss(row.get('Location', '')),
                        circuit_key=ss(row.get('CircuitShortName', '')),
                    )
                    db.add(event); db.flush()

                # Load race session with rate limiting
                try:
                    print(f"    R{round_num}: {event_name} ... ", end='', flush=True)
                    
                    # Rate limit delay
                    if api_calls > 0 and api_calls % 5 == 0:
                        delay = 8
                        print(f"(rate limit pause {delay}s) ", end='', flush=True)
                        time.sleep(delay)

                    race = fastf1.get_session(year, round_num, 'R')
                    race.load(telemetry=False, weather=(year >= 2018), messages=False, laps=(year >= 2018))
                    api_calls += 1

                    try: session_date = race.date
                    except: session_date = event.event_date
                    try: total_laps = si(race.total_laps)
                    except: total_laps = None

                    sess = Session(event_id=event.event_id, session_type='R',
                                   session_date=session_date, total_laps=total_laps)
                    db.add(sess); db.flush()

                    results = race.results
                    drivers_seen = set()
                    if results is not None and len(results) > 0:
                        for _, r in results.iterrows():
                            code = ss(r.get('Abbreviation', ''))
                            if not code or code in drivers_seen: continue
                            drivers_seen.add(code)

                            driver = get_or_create_driver(db, code,
                                ss(r.get('FirstName', '')), ss(r.get('LastName', '')),
                                ss(r.get('CountryCode', '')), ss(r.get('TeamName', '')),
                                si(r.get('DriverNumber')))
                            if not driver: continue

                            pos = si(r.get('Position'))
                            grid = si(r.get('GridPosition'))
                            pts = sf(r.get('Points', 0))
                            status = ss(r.get('Status', 'Unknown'))
                            is_dnf = status.lower() not in ['finished', '+1 lap', '+2 laps', '+3 laps', '+4 laps', '+5 laps', '']
                            if 'lap' in status.lower() and status.startswith('+'): is_dnf = False

                            ds = DriverSession(session_id=sess.session_id, driver_id=driver.driver_id,
                                             position=pos, grid=grid, points=pts, status=status,
                                             dnf=is_dnf, dnf_reason=status if is_dnf else None)
                            db.add(ds); db.flush()

                            # Lap data for recent seasons
                            if year >= 2018:
                                try:
                                    laps_df = race.laps.pick_driver(code)
                                    if laps_df is not None and len(laps_df) > 0:
                                        for _, lr in laps_df.iterrows():
                                            ln = si(lr.get('LapNumber'))
                                            if ln is None: continue
                                            lap = Lap(driver_session_id=ds.driver_session_id, lap_number=ln,
                                                     lap_time=td_sec(lr.get('LapTime')),
                                                     sector1_time=td_sec(lr.get('Sector1Time')),
                                                     sector2_time=td_sec(lr.get('Sector2Time')),
                                                     sector3_time=td_sec(lr.get('Sector3Time')),
                                                     position=si(lr.get('Position')),
                                                     tyre_compound=ss(lr.get('Compound', '')),
                                                     tyre_age=si(lr.get('TyreLife')),
                                                     is_personal_best=bool(lr.get('IsPersonalBest', False)) if not pd.isna(lr.get('IsPersonalBest', False)) else False,
                                                     pit_out_lap=bool(lr.get('PitOutTime') is not None and not pd.isna(lr.get('PitOutTime'))),
                                                     pit_in_lap=bool(lr.get('PitInTime') is not None and not pd.isna(lr.get('PitInTime'))),
                                                     is_accurate=bool(lr.get('IsAccurate', True)) if not pd.isna(lr.get('IsAccurate', True)) else True)
                                            db.add(lap)
                                except: pass

                    # Weather
                    if year >= 2018:
                        try:
                            wdf = race.weather_data
                            if wdf is not None and len(wdf) > 0:
                                interval = max(1, len(wdf) // 20)
                                for i in range(0, len(wdf), interval):
                                    w = wdf.iloc[i]
                                    db.add(Weather(session_id=sess.session_id,
                                                  air_temp=sf(w.get('AirTemp')), track_temp=sf(w.get('TrackTemp')),
                                                  humidity=si(w.get('Humidity')), pressure=sf(w.get('Pressure')),
                                                  wind_speed=sf(w.get('WindSpeed')), wind_direction=si(w.get('WindDirection')),
                                                  rainfall=bool(w.get('Rainfall', False)) if not pd.isna(w.get('Rainfall', False)) else False))
                        except: pass

                    dc = len(drivers_seen)
                    print(f"→ {dc} drivers")

                except Exception as e:
                    db.rollback()
                    err = str(e)[:60]
                    if '500 calls' in err or 'rate' in err.lower():
                        print(f"RATE LIMITED! Waiting 60s...")
                        time.sleep(60)
                        api_calls = 0
                    else:
                        print(f"Error: {err}")

                try: db.commit()
                except: db.rollback()

            db.commit()
            # Check results
            new_sessions = db.query(Session.session_id).join(Event).filter(Event.season == year).count()
            new_events = db.query(Event).filter(Event.season == year).count()
            print(f"  ✓ {year}: {new_events} events, {new_sessions} sessions")

        elapsed = time.time() - start
        total_ev = db.query(Event).count()
        total_sess = db.query(Session).count()
        total_ds = db.query(DriverSession).count()
        total_drv = db.query(Driver).count()
        print(f"\n{'=' * 60}")
        print(f"  PATCH COMPLETE ({elapsed:.0f}s)")
        print(f"  Events: {total_ev}, Sessions: {total_sess}")
        print(f"  Drivers: {total_drv}, Results: {total_ds}")
        print(f"{'=' * 60}")

    except Exception as e:
        import traceback
        print(f"\nFATAL: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    patch_missing()
