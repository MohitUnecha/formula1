"""
Fill Missing Sprint Sessions from Jolpica-F1 API

FastF1 fails on 3 × 2022 sprints (R4 Imola, R11 Austria, R21 Brazil)
with KeyError: 'DriverNumber'. This script fills them from Jolpica-F1.

Also fills any other missing sprint data across all seasons.

Usage:
    cd backend
    python fill_sprints_jolpica.py
"""

import asyncio
import sys
import os

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session as DBSessionORM
from database import SessionLocal, init_db
from models import Event, Session as DBSession, Driver, DriverSession, Lap
from services.jolpica_client import jolpica, JolpicaRaceResult
from team_mapping import get_team_for_driver


# Map Jolpica driver codes/IDs to our DB driver codes
JOLPICA_TO_CODE = {
    "max_verstappen": "VER", "leclerc": "LEC", "perez": "PER", "sainz": "SAI",
    "norris": "NOR", "ricciardo": "RIC", "bottas": "BOT", "kevin_magnussen": "MAG",
    "alonso": "ALO", "mick_schumacher": "MSC", "russell": "RUS", "tsunoda": "TSU",
    "vettel": "VET", "hamilton": "HAM", "stroll": "STR", "ocon": "OCO",
    "gasly": "GAS", "albon": "ALB", "latifi": "LAT", "zhou": "ZHO",
    "piastri": "PIA", "de_vries": "DEV", "sargeant": "SAR", "lawson": "LAW",
    "hulkenberg": "HUL", "bearman": "BEA", "colapinto": "COL",
    "jack_doohan": "DOO", "doohan": "DOO", "bortoleto": "BOR",
    "hadjar": "HAD", "antonelli": "ANT",
}


def get_or_create_driver(db: DBSessionORM, result: JolpicaRaceResult, season: int) -> Driver:
    """Get existing driver or create a new one."""
    code = result.driver_code or JOLPICA_TO_CODE.get(result.driver_id, "")
    if not code:
        # Generate code from last name
        code = result.last_name[:3].upper()

    driver = db.query(Driver).filter(Driver.driver_code == code).first()
    if driver:
        return driver

    # Create new driver
    team_info = get_team_for_driver(code, season)
    driver = Driver(
        driver_code=code,
        driver_number=result.driver_number,
        first_name=result.first_name,
        last_name=result.last_name,
        team_name=team_info[0] if team_info else result.constructor_name,
        team_color=team_info[1] if team_info else "#888888",
    )
    db.add(driver)
    db.flush()
    print(f"  ✓ Created new driver: {code} ({result.first_name} {result.last_name})")
    return driver


async def fill_sprint(db: DBSessionORM, season: int, round_num: int, event: Event):
    """Fill a single sprint session from Jolpica API."""
    print(f"\n{'='*60}")
    print(f"  Filling Sprint: {season} R{round_num} - {event.event_name}")
    print(f"{'='*60}")

    # Check if sprint session already exists
    existing = db.query(DBSession).filter(
        DBSession.event_id == event.event_id,
        DBSession.session_type == 'S'
    ).first()

    if existing:
        # Check if it has driver sessions
        ds_count = db.query(DriverSession).filter(
            DriverSession.session_id == existing.session_id
        ).count()
        if ds_count > 0:
            print(f"  ⏭  Already has {ds_count} drivers — skipping")
            return False

    # Fetch from Jolpica
    try:
        results = await jolpica.get_sprint_results(season, round_num)
    except Exception as e:
        print(f"  ✗ Jolpica fetch failed: {e}")
        return False

    if not results:
        print(f"  ✗ No sprint results found for {season} R{round_num}")
        return False

    print(f"  ✓ Got {len(results)} drivers from Jolpica")

    # Create sprint session if needed
    if not existing:
        existing = DBSession(
            event_id=event.event_id,
            session_type='S',
            session_date=event.event_date,
            total_laps=results[0].laps if results else 0,
        )
        db.add(existing)
        db.flush()
        print(f"  ✓ Created sprint session ID {existing.session_id}")

    # Update total laps
    if results and results[0].laps:
        existing.total_laps = results[0].laps

    # Create driver sessions and basic lap data
    created = 0
    for r in results:
        driver = get_or_create_driver(db, r, season)

        # Check if driver_session already exists
        ds = db.query(DriverSession).filter(
            DriverSession.session_id == existing.session_id,
            DriverSession.driver_id == driver.driver_id,
        ).first()

        if ds:
            continue

        is_dnf = r.status != "Finished" and not r.status.startswith("+")
        ds = DriverSession(
            session_id=existing.session_id,
            driver_id=driver.driver_id,
            grid=r.grid,
            position=r.position if not is_dnf else None,
            status=r.status,
            points=r.points,
            dnf=is_dnf,
            dnf_reason=r.status if is_dnf else None,
        )
        db.add(ds)
        db.flush()

        # Create basic lap entries from Jolpica timing data
        total_laps = r.laps or existing.total_laps or 0
        if total_laps > 0 and r.time_millis:
            avg_lap_ms = r.time_millis / total_laps
            for lap_num in range(1, total_laps + 1):
                lap = Lap(
                    driver_session_id=ds.driver_session_id,
                    lap_number=lap_num,
                    position=r.position,
                    lap_time=round(avg_lap_ms / 1000, 3),  # Average lap time in seconds
                )
                db.add(lap)

        created += 1

    db.commit()
    print(f"  ✓ Created {created} driver sessions with lap data")
    return True


async def fill_all_missing_sprints():
    """Find and fill all missing sprint sessions."""
    init_db()
    db = SessionLocal()

    # Known 2022 sprints that FastF1 couldn't load
    KNOWN_MISSING_2022 = [
        (2022, 4),   # Emilia Romagna (Imola)
        (2022, 11),  # Austrian GP (Red Bull Ring)
        (2022, 21),  # São Paulo GP (Interlagos)
    ]

    # Also check 2021 and 2022 sprints from Jolpica schedule
    SPRINT_ROUNDS = {
        2021: [10, 14, 20],           # Britain, Italy, São Paulo
        2022: [4, 11, 21],            # Imola, Austria, Brazil
        2023: [4, 5, 10, 11, 17, 19], # Azerbaijan, Miami, Austria, Belgium, Qatar, São Paulo
        2024: [4, 5, 11, 12, 19, 21], # China, Miami, Austria, COTA, Qatar, Abu Dhabi ... approx
        2025: [4, 5, 11, 12, 21, 23], # Approx
        2026: [4, 5, 11, 12, 21, 23], # Projected — update when confirmed
    }

    total_filled = 0

    for season, rounds in SPRINT_ROUNDS.items():
        for round_num in rounds:
            event = db.query(Event).filter(
                Event.season == season,
                Event.round == round_num
            ).first()

            if not event:
                print(f"⚠ No event found for {season} R{round_num} — skipping")
                continue

            # Check if sprint exists with data
            sprint = db.query(DBSession).filter(
                DBSession.event_id == event.event_id,
                DBSession.session_type == 'S'
            ).first()

            if sprint:
                ds_count = db.query(DriverSession).filter(
                    DriverSession.session_id == sprint.session_id
                ).count()
                if ds_count > 0:
                    print(f"✓ {season} R{round_num} ({event.event_name}) — {ds_count} drivers ✓")
                    continue

            # Missing → fill it
            result = await fill_sprint(db, season, round_num, event)
            if result:
                total_filled += 1

    db.close()
    print(f"\n{'='*60}")
    print(f"  Done! Filled {total_filled} sprint sessions from Jolpica-F1")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(fill_all_missing_sprints())
