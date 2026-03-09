#!/usr/bin/env python3
"""Quick check what session types exist in the DB."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import SessionLocal
from models import Session as DBSession, Event, DriverSession, Lap
from sqlalchemy import func

db = SessionLocal()

# Count sessions by type
types = db.query(DBSession.session_type, func.count(DBSession.session_id)).group_by(DBSession.session_type).all()
print("Session types in DB:")
for t, c in sorted(types, key=lambda x: -x[1]):
    print(f"  {t}: {c}")

# FP/Q by season
fp_q = (
    db.query(DBSession.session_type, Event.season, func.count(DBSession.session_id))
    .join(Event)
    .filter(DBSession.session_type.in_(["FP1","FP2","FP3","Q","SQ"]))
    .group_by(DBSession.session_type, Event.season)
    .all()
)
print("\nFP/Q sessions by season:")
for t, s, c in sorted(fp_q, key=lambda x: (x[1], x[0])):
    print(f"  {s} {t}: {c}")

# Find a season with FP/Q data
for season in [2026, 2025, 2024, 2023, 2022]:
    events = db.query(Event).filter(Event.season == season).limit(5).all()
    for e in events:
        sessions = db.query(DBSession).filter(DBSession.event_id == e.event_id).all()
        stypes = [s.session_type for s in sessions]
        for st in ["FP1","FP2","FP3","Q"]:
            if st in stypes:
                s_obj = next(s for s in sessions if s.session_type == st)
                lap_count = (
                    db.query(func.count(Lap.lap_id))
                    .join(DriverSession)
                    .filter(DriverSession.session_id == s_obj.session_id)
                    .scalar()
                )
                driver_count = (
                    db.query(func.count(DriverSession.driver_session_id))
                    .filter(DriverSession.session_id == s_obj.session_id)
                    .scalar()
                )
                print(f"\n  Sample: {season} {e.event_name} {st} (sid={s_obj.session_id}): {driver_count} drivers, {lap_count} laps")
                if lap_count > 0:
                    print("  ^ HAS lap data!")

db.close()
