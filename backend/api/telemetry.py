"""
API Router: Telemetry & Analysis

Real telemetry and analysis endpoints using lap data from the database,
enriched with OpenF1 live data and Jolpica historical data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from pydantic import BaseModel
import logging

from database import get_db
from models import (
    Session as DBSession, DriverSession, Driver, Lap, Event, Weather, PitStop
)
from services.openf1_client import openf1
from services.jolpica_client import jolpica
from team_mapping import get_team_for_driver

# ─── Telemetry Router ──────────────────────────────────────────────
telemetry_router = APIRouter()


class LapTelemetry(BaseModel):
    lap_number: int
    lap_time: Optional[float] = None
    sector1: Optional[float] = None
    sector2: Optional[float] = None
    sector3: Optional[float] = None
    position: Optional[int] = None
    tyre_compound: Optional[str] = None
    tyre_age: Optional[int] = None
    pit_in: bool = False
    pit_out: bool = False
    is_personal_best: bool = False

    class Config:
        from_attributes = True


@telemetry_router.get("/telemetry/{session_id}/{driver_code}")
async def get_telemetry(
    session_id: int,
    driver_code: str,
    db: Session = Depends(get_db)
):
    """Get lap-by-lap telemetry for a driver in a session"""
    driver = db.query(Driver).filter(Driver.driver_code == driver_code.upper()).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    ds = db.query(DriverSession).filter(
        DriverSession.session_id == session_id,
        DriverSession.driver_id == driver.driver_id
    ).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Driver not in this session")

    laps = db.query(Lap).filter(
        Lap.driver_session_id == ds.driver_session_id
    ).order_by(Lap.lap_number).all()

    return {
        "driver_code": driver_code.upper(),
        "session_id": session_id,
        "position": ds.position,
        "grid": ds.grid,
        "status": ds.status,
        "total_laps": len(laps),
        "laps": [
            LapTelemetry(
                lap_number=lap.lap_number,
                lap_time=float(lap.lap_time) if lap.lap_time else None,
                sector1=float(lap.sector1_time) if lap.sector1_time else None,
                sector2=float(lap.sector2_time) if lap.sector2_time else None,
                sector3=float(lap.sector3_time) if lap.sector3_time else None,
                position=lap.position,
                tyre_compound=lap.tyre_compound or "",
                tyre_age=lap.tyre_age,
                pit_in=lap.pit_in_lap or False,
                pit_out=lap.pit_out_lap or False,
                is_personal_best=lap.is_personal_best or False,
            )
            for lap in laps
        ]
    }


# ─── Analysis Router ───────────────────────────────────────────────
analysis_router = APIRouter()


class DriverLapStats(BaseModel):
    driver_code: str
    driver_name: str
    team: str
    position: Optional[int] = None
    total_laps: int
    avg_lap_time: Optional[float] = None
    best_lap_time: Optional[float] = None
    worst_lap_time: Optional[float] = None
    median_lap_time: Optional[float] = None
    stint_count: int = 0
    tyre_compounds: List[str] = []

    class Config:
        from_attributes = True


@analysis_router.get("/analysis/lap-times/{session_id}")
async def get_lap_times(session_id: int, db: Session = Depends(get_db)):
    """Get lap time analysis for all drivers in a session"""
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).order_by(DriverSession.position).all()

    event = db.query(Event).filter(Event.event_id == session.event_id).first()
    season = event.season if event else 0

    result = []
    for ds in driver_sessions:
        laps = db.query(Lap).filter(
            Lap.driver_session_id == ds.driver_session_id,
            Lap.lap_time.isnot(None),
            Lap.lap_time > 0
        ).all()

        lap_times = [float(l.lap_time) for l in laps if l.lap_time]
        compounds = list(set(l.tyre_compound for l in laps if l.tyre_compound))
        pit_count = sum(1 for l in laps if l.pit_in_lap)

        avg_t = sum(lap_times) / len(lap_times) if lap_times else None
        best_t = min(lap_times) if lap_times else None
        worst_t = max(lap_times) if lap_times else None
        median_t = sorted(lap_times)[len(lap_times) // 2] if lap_times else None

        team_info = get_team_for_driver(ds.driver.driver_code, season) if season else None
        team_name = team_info[0] if team_info else (ds.driver.team_name or "")

        result.append(DriverLapStats(
            driver_code=ds.driver.driver_code,
            driver_name=f"{ds.driver.first_name} {ds.driver.last_name}",
            team=team_name,
            position=ds.position,
            total_laps=len(laps),
            avg_lap_time=round(avg_t, 3) if avg_t else None,
            best_lap_time=round(best_t, 3) if best_t else None,
            worst_lap_time=round(worst_t, 3) if worst_t else None,
            median_lap_time=round(median_t, 3) if median_t else None,
            stint_count=pit_count + 1,
            tyre_compounds=compounds,
        ))

    return {
        "session_id": session_id,
        "event_name": session.event.event_name if session.event else "",
        "drivers": result
    }


@analysis_router.get("/analysis/position-changes/{session_id}")
async def get_position_changes(session_id: int, db: Session = Depends(get_db)):
    """Get lap-by-lap position changes for all drivers in a race"""
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).order_by(DriverSession.position).all()

    event = db.query(Event).filter(Event.event_id == session.event_id).first()
    season = event.season if event else 0

    position_data = {}
    for ds in driver_sessions:
        laps = db.query(Lap).filter(
            Lap.driver_session_id == ds.driver_session_id
        ).order_by(Lap.lap_number).all()

        team_info = get_team_for_driver(ds.driver.driver_code, season) if season else None
        team_name = team_info[0] if team_info else (ds.driver.team_name or "")
        team_color = team_info[1] if team_info else (ds.driver.team_color or "#888888")

        position_data[ds.driver.driver_code] = {
            "driver_code": ds.driver.driver_code,
            "driver_name": f"{ds.driver.first_name} {ds.driver.last_name}",
            "team": team_name,
            "team_color": team_color,
            "grid": ds.grid,
            "finish": ds.position,
            "positions": [
                {"lap": lap.lap_number, "position": lap.position}
                for lap in laps if lap.position
            ]
        }

    return {
        "session_id": session_id,
        "drivers": position_data
    }


@analysis_router.get("/analysis/tyre-strategy/{session_id}")
async def get_tyre_strategy(session_id: int, db: Session = Depends(get_db)):
    """Get tyre strategy data for all drivers"""
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    event = db.query(Event).filter(Event.event_id == session.event_id).first() if session else None
    season = event.season if event else 0

    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).order_by(DriverSession.position).all()

    strategies = []
    for ds in driver_sessions:
        laps = db.query(Lap).filter(
            Lap.driver_session_id == ds.driver_session_id,
        ).order_by(Lap.lap_number).all()

        stints = []
        current_compound = None
        stint_start = 1
        for lap in laps:
            compound = lap.tyre_compound or "UNKNOWN"
            if compound != current_compound:
                if current_compound:
                    stints.append({
                        "compound": current_compound,
                        "start_lap": stint_start,
                        "end_lap": lap.lap_number - 1,
                        "laps": lap.lap_number - stint_start
                    })
                current_compound = compound
                stint_start = lap.lap_number
        if current_compound and laps:
            stints.append({
                "compound": current_compound,
                "start_lap": stint_start,
                "end_lap": laps[-1].lap_number,
                "laps": laps[-1].lap_number - stint_start + 1
            })

        team_info = get_team_for_driver(ds.driver.driver_code, season) if season else None
        strat_team = team_info[0] if team_info else (ds.driver.team_name or "")

        strategies.append({
            "driver_code": ds.driver.driver_code,
            "driver_name": f"{ds.driver.first_name} {ds.driver.last_name}",
            "team": strat_team,
            "position": ds.position,
            "stints": stints,
            "total_pit_stops": len(stints) - 1 if stints else 0
        })

    return {
        "session_id": session_id,
        "strategies": strategies
    }


logger = logging.getLogger(__name__)


# ─── Enriched Analysis Endpoints (OpenF1 + Jolpica) ───────────────

@analysis_router.get("/analysis/speed-traps/{session_id}")
async def get_speed_traps(session_id: int, db: Session = Depends(get_db)):
    """
    Get speed trap data from OpenF1 for a session.
    Shows max speeds per driver at various track sections.
    """
    session = db.query(DBSession).join(Event).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    event = session.event
    season = event.season if event else 2024
    event_name = (event.event_name or "").lower() if event else ""

    try:
        # Map session to OpenF1
        session_type_map = {"R": "Race", "Q": "Qualifying", "S": "Sprint"}
        of1_type = session_type_map.get(session.session_type, "Race")
        of1_sessions = await openf1.get_sessions(season, of1_type)
        matching = [s for s in of1_sessions if event_name[:6] in s.circuit_short_name.lower() or s.location.lower() in event_name]

        if not matching:
            return {"session_id": session_id, "speed_data": [], "source": "unavailable"}

        of1_session = matching[-1]
        car_data = await openf1.get_car_data(of1_session.session_key)

        # Aggregate max speed per driver
        driver_speeds: Dict[str, list] = {}
        for cd in car_data:
            code = str(cd.driver_number)
            driver_speeds.setdefault(code, []).append(cd.speed)

        speed_results = []
        for driver_num, speeds in driver_speeds.items():
            if speeds:
                speed_results.append({
                    "driver_number": driver_num,
                    "max_speed": max(speeds),
                    "avg_speed": round(sum(speeds) / len(speeds), 1),
                    "samples": len(speeds),
                })

        speed_results.sort(key=lambda x: x["max_speed"], reverse=True)
        return {
            "session_id": session_id,
            "event_name": event.event_name,
            "speed_data": speed_results[:20],
            "source": "OpenF1",
        }
    except Exception as e:
        logger.warning(f"Speed trap data unavailable: {e}")
        return {"session_id": session_id, "speed_data": [], "source": "error", "detail": str(e)}


@analysis_router.get("/analysis/intervals/{session_id}")
async def get_race_intervals(session_id: int, db: Session = Depends(get_db)):
    """
    Get live interval data from OpenF1 — gaps between drivers during the race.
    """
    session = db.query(DBSession).join(Event).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    event = session.event
    try:
        of1_sessions = await openf1.get_sessions(event.season if event else 2024, "Race")
        event_name = (event.event_name or "").lower() if event else ""
        matching = [s for s in of1_sessions if event_name[:6] in s.circuit_short_name.lower()]

        if not matching:
            return {"session_id": session_id, "intervals": [], "source": "unavailable"}

        intervals = await openf1.get_intervals(matching[-1].session_key)
        return {
            "session_id": session_id,
            "event_name": event.event_name if event else "",
            "intervals": [
                {
                    "driver_number": iv.driver_number,
                    "gap_to_leader": iv.gap_to_leader,
                    "interval": iv.interval,
                    "date": iv.date,
                }
                for iv in intervals[:500]  # limit to prevent huge responses
            ],
            "source": "OpenF1",
        }
    except Exception as e:
        logger.warning(f"Intervals unavailable: {e}")
        return {"session_id": session_id, "intervals": [], "source": "error"}


@analysis_router.get("/analysis/weather-correlation/{session_id}")
async def get_weather_correlation(session_id: int, db: Session = Depends(get_db)):
    """
    Get weather data during a session and correlate with driver performance.
    Combines DB weather + OpenF1 live weather.
    """
    session = db.query(DBSession).join(Event).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # DB weather
    db_weather = db.query(Weather).filter(Weather.session_id == session_id).all()
    weather_timeline = [
        {
            "time": w.created_at.isoformat() if w.created_at else None,
            "lap_number": w.lap_number,
            "air_temp": w.air_temp,
            "track_temp": w.track_temp,
            "humidity": w.humidity,
            "rainfall": w.rainfall,
            "wind_speed": w.wind_speed,
        }
        for w in db_weather
    ]

    # Try OpenF1 enrichment
    event = session.event
    of1_weather = []
    try:
        of1_sessions = await openf1.get_sessions(event.season if event else 2024)
        event_name = (event.event_name or "").lower() if event else ""
        matching = [s for s in of1_sessions if event_name[:6] in s.circuit_short_name.lower()]
        if matching:
            of1_data = await openf1.get_weather(matching[-1].session_key)
            of1_weather = [
                {
                    "air_temp": w.air_temperature,
                    "track_temp": w.track_temperature,
                    "humidity": w.humidity,
                    "rainfall": w.rainfall,
                    "wind_speed": w.wind_speed,
                    "wind_direction": w.wind_direction,
                    "pressure": w.pressure,
                    "date": w.date,
                }
                for w in of1_data
            ]
    except Exception as e:
        logger.warning(f"OpenF1 weather unavailable: {e}")

    # Performance in session
    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).order_by(DriverSession.position).all()

    had_rain = any(w.rainfall for w in db_weather) if db_weather else False
    if not had_rain and of1_weather:
        had_rain = any(w.get("rainfall", False) for w in of1_weather)

    results = [
        {
            "driver_code": ds.driver.driver_code,
            "position": ds.position,
            "grid": ds.grid,
            "positions_gained": (ds.grid - ds.position) if ds.grid and ds.position else None,
        }
        for ds in driver_sessions
    ]

    return {
        "session_id": session_id,
        "event_name": event.event_name if event else "",
        "had_rain": had_rain,
        "db_weather": weather_timeline,
        "openf1_weather": of1_weather,
        "driver_results": results,
    }


@analysis_router.get("/analysis/pit-performance/{session_id}")
async def get_pit_performance(session_id: int, db: Session = Depends(get_db)):
    """
    Get detailed pit stop performance data, combining DB + Jolpica.
    """
    session = db.query(DBSession).join(Event).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    event = session.event

    # DB pit stops via DriverSession
    db_pit_data = []
    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).all()
    for ds in driver_sessions:
        db_pits = db.query(PitStop).filter(PitStop.driver_session_id == ds.driver_session_id).all()
        for ps in db_pits:
            db_pit_data.append({
                "driver_code": ds.driver.driver_code,
                "lap": ps.lap_number,
                "duration": float(ps.pit_duration) if ps.pit_duration else None,
                "old_compound": ps.tyre_compound_old,
                "new_compound": ps.tyre_compound_new,
                "source": "database",
            })

    # Jolpica pit stops (richer data)
    jolpica_pit_data = []
    try:
        if event:
            jol_pits = await jolpica.get_pit_stops(event.season, event.round)
            jolpica_pit_data = [
                {
                    "driver_code": ps.driver_code,
                    "lap": ps.lap,
                    "stop_number": ps.stop_number,
                    "duration_str": ps.duration,
                    "duration_ms": ps.duration_millis,
                    "duration_s": round(ps.duration_millis / 1000, 3) if ps.duration_millis else None,
                    "source": "jolpica",
                }
                for ps in jol_pits
            ]
    except Exception as e:
        logger.warning(f"Jolpica pit stops unavailable: {e}")

    # Team averages
    team_avgs: Dict[str, list] = {}
    for ps in jolpica_pit_data:
        if ps["duration_ms"]:
            from team_mapping import get_team_for_driver
            ti = get_team_for_driver(ps["driver_code"], event.season if event else 2024)
            team = ti[0] if ti else "Unknown"
            team_avgs.setdefault(team, []).append(ps["duration_ms"] / 1000.0)

    team_summary = {
        team: {
            "avg_pit_time": round(sum(times) / len(times), 3),
            "fastest": round(min(times), 3),
            "slowest": round(max(times), 3),
            "stops": len(times),
        }
        for team, times in team_avgs.items()
    }

    return {
        "session_id": session_id,
        "event_name": event.event_name if event else "",
        "db_pit_stops": db_pit_data,
        "jolpica_pit_stops": jolpica_pit_data,
        "team_summary": team_summary,
    }


@analysis_router.get("/analysis/driver-comparison")
async def get_driver_comparison(
    driver_a: str = Query(...),
    driver_b: str = Query(...),
    season: int = Query(default=2024),
    db: Session = Depends(get_db)
):
    """
    Head-to-head comparison of two drivers using DB + external APIs.
    """
    def get_driver_stats(code: str):
        driver = db.query(Driver).filter(Driver.driver_code == code.upper()).first()
        if not driver:
            return None

        results = db.query(DriverSession).join(DBSession).join(Event).filter(
            DriverSession.driver_id == driver.driver_id,
            Event.season == season,
            DriverSession.position.isnot(None),
        ).all()

        positions = [r.position for r in results if r.position]
        grids = [r.grid for r in results if r.grid]

        ti = get_team_for_driver(code.upper(), season)
        resolved_team = ti[0] if ti else (driver.team_name or "")

        return {
            "driver_code": code.upper(),
            "driver_name": f"{driver.first_name} {driver.last_name}",
            "team": resolved_team,
            "races": len(results),
            "wins": sum(1 for p in positions if p == 1),
            "podiums": sum(1 for p in positions if p <= 3),
            "avg_position": round(sum(positions) / len(positions), 2) if positions else None,
            "avg_grid": round(sum(grids) / len(grids), 2) if grids else None,
            "best_finish": min(positions) if positions else None,
            "dnfs": sum(1 for r in results if r.dnf),
            "points": sum(float(r.points or 0) for r in results),
            "positions_gained_avg": round(
                sum((g - p) for g, p in zip(grids, positions) if g and p) / max(len(positions), 1), 2
            ) if positions and grids else 0,
        }

    stats_a = get_driver_stats(driver_a)
    stats_b = get_driver_stats(driver_b)

    if not stats_a or not stats_b:
        raise HTTPException(status_code=404, detail="One or both drivers not found")

    # Enrich with Jolpica current standings
    try:
        standings = await jolpica.get_driver_standings(season)
        for s in standings:
            if s.driver_code == driver_a.upper():
                stats_a["championship_position"] = s.position
                stats_a["championship_points"] = s.points
            elif s.driver_code == driver_b.upper():
                stats_b["championship_position"] = s.position
                stats_b["championship_points"] = s.points
    except Exception:
        pass

    # Elo comparison
    try:
        from services.elo_rating import get_elo_system
        elo = get_elo_system(db)
        ea = elo.get_driver_elo(driver_a.upper())
        eb = elo.get_driver_elo(driver_b.upper())
        h2h_prob = elo.head_to_head(driver_a.upper(), driver_b.upper())
        stats_a["elo_rating"] = round(ea.rating, 1) if ea else None
        stats_a["elo_tier"] = ea.tier if ea else None
        stats_b["elo_rating"] = round(eb.rating, 1) if eb else None
        stats_b["elo_tier"] = eb.tier if eb else None
    except Exception:
        h2h_prob = 0.5

    return {
        "season": season,
        "driver_a": stats_a,
        "driver_b": stats_b,
        "elo_head_to_head": {
            "prob_a_beats_b": round(h2h_prob, 4),
            "prob_b_beats_a": round(1 - h2h_prob, 4),
        }
    }


# Export routers
router = telemetry_router
telemetry = telemetry_router
analysis = analysis_router
