"""
API Router: Replay

Endpoints for race replay using real lap data from the database.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import math

from database import get_db
from models import Session as DBSession, DriverSession, Driver, Lap, Event, Weather
from team_mapping import get_team_for_driver, get_driver_name

router = APIRouter()


class TrackLayout(BaseModel):
    circuit_key: str
    rotation: int = 0
    corners: List[dict]
    width: int = 1600
    height: int = 1100


class ReplayMetadata(BaseModel):
    session_id: int
    event_name: str = ""
    season: int = 0
    total_laps: int
    total_frames: int
    fps: int
    drivers: List[dict]
    track_layout: TrackLayout


class DriverFrame(BaseModel):
    code: str
    position: int
    x: float
    y: float
    speed: float
    tyre: str = ""
    tyre_age: int = 0
    gap_to_leader: float = 0.0
    gap_to_ahead: float = 0.0
    team_color: str = "#888888"
    team_name: str = ""
    lap_time: Optional[float] = None
    track_progress: float = 0.0  # 0.0 to 1.0 position on track


class ReplayFrame(BaseModel):
    lap: int
    time_elapsed: float
    drivers: List[DriverFrame]
    track_status: str = "Green"
    flags: List[str] = []


class RaceEvent(BaseModel):
    lap: int
    time: float
    type: str
    driver: Optional[str] = None
    details: str


# ─── Track layouts for popular circuits ─────────────────────────
TRACK_POINTS = {
    "default": [
        (400, 150), (600, 100), (900, 100), (1100, 150),
        (1300, 250), (1400, 400), (1350, 600), (1200, 750),
        (1000, 850), (700, 900), (400, 850), (250, 700),
        (200, 500), (250, 300), (350, 200),
    ],
}


def get_track_points(circuit_key: str) -> list:
    key = (circuit_key or "").lower()
    return TRACK_POINTS.get(key, TRACK_POINTS["default"])


def interpolate_track_position(track_points: list, progress: float):
    """Get (x, y) position on track at given progress (0.0 to 1.0)"""
    n = len(track_points)
    if n < 2:
        return track_points[0] if track_points else (800, 550)

    total = progress * n
    idx = int(total) % n
    frac = total - int(total)

    p1 = track_points[idx]
    p2 = track_points[(idx + 1) % n]

    x = p1[0] + (p2[0] - p1[0]) * frac
    y = p1[1] + (p2[1] - p1[1]) * frac
    return (x, y)


@router.get("/replay/{session_id}/metadata", response_model=ReplayMetadata)
async def get_replay_metadata(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get metadata for race replay"""
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    event = db.query(Event).filter(Event.event_id == session.event_id).first()

    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).order_by(DriverSession.grid).all()

    drivers = []
    season = event.season if event else 0
    for ds in driver_sessions:
        team_info = get_team_for_driver(ds.driver.driver_code, season) if season else None
        team_name = team_info[0] if team_info else (ds.driver.team_name or "")
        team_color = team_info[1] if team_info else (ds.driver.team_color or "#888888")
        name_override = get_driver_name(ds.driver.driver_code, season) if season else None
        if name_override:
            display_name = f"{name_override[0]} {name_override[1]}"
        else:
            display_name = f"{ds.driver.first_name} {ds.driver.last_name}"
        drivers.append({
            "code": ds.driver.driver_code,
            "name": display_name,
            "team": team_name,
            "color": team_color,
            "grid": ds.grid,
            "position": ds.position,
            "status": ds.status or "",
        })

    circuit_key = (event.circuit_key or "default") if event else "default"
    track_points = get_track_points(circuit_key)

    total_laps = session.total_laps or 60
    fps = 2  # 2 frames per lap (start + end)

    return ReplayMetadata(
        session_id=session_id,
        event_name=event.event_name if event else "",
        season=event.season if event else 0,
        total_laps=total_laps,
        total_frames=total_laps * fps,
        fps=fps,
        drivers=drivers,
        track_layout=TrackLayout(
            circuit_key=circuit_key,
            corners=[{"x": p[0], "y": p[1]} for p in track_points],
        )
    )


@router.get("/replay/{session_id}/frames")
async def get_replay_frames(
    session_id: int,
    start_lap: int = Query(1, ge=1),
    end_lap: int = Query(999, ge=1),
    db: Session = Depends(get_db)
):
    """
    Get position frames for replay.
    Returns per-lap position data with interpolated track positions.
    """
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    event = db.query(Event).filter(Event.event_id == session.event_id).first()
    circuit_key = (event.circuit_key or "default") if event else "default"
    track_points = get_track_points(circuit_key)

    # Clamp end_lap
    if session.total_laps and end_lap > session.total_laps:
        end_lap = session.total_laps

    # Get all drivers
    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).all()

    if not driver_sessions:
        return {"frames": [], "total_laps": 0}

    # Build driver metadata map
    event = db.query(Event).filter(Event.event_id == session.event_id).first()
    season = event.season if event else 0
    
    ds_map = {}
    for ds in driver_sessions:
        team_info = get_team_for_driver(ds.driver.driver_code, season) if season else None
        team_color = team_info[1] if team_info else (ds.driver.team_color or "#888888")
        team_name = team_info[0] if team_info else (ds.driver.team_name or "")
        ds_map[ds.driver_session_id] = {
            "code": ds.driver.driver_code,
            "team_color": team_color,
            "team_name": team_name,
            "grid": ds.grid or 20,
            "final_pos": ds.position or 20,
        }

    # Get all laps for this session in range
    all_laps = db.query(Lap).filter(
        Lap.driver_session_id.in_([ds.driver_session_id for ds in driver_sessions]),
        Lap.lap_number >= start_lap,
        Lap.lap_number <= end_lap,
    ).order_by(Lap.lap_number).all()

    # Group laps by lap number
    laps_by_number = {}
    for lap in all_laps:
        laps_by_number.setdefault(lap.lap_number, []).append(lap)

    frames = []
    cumulative_time = 0.0

    # If no lap data, generate from grid/finish positions
    if not all_laps:
        for lap_num in range(start_lap, min(end_lap + 1, (session.total_laps or 60) + 1)):
            driver_frames = []
            for ds in driver_sessions:
                meta = ds_map[ds.driver_session_id]
                # Interpolate position from grid to finish
                total = session.total_laps or 60
                progress = lap_num / total
                current_pos = meta["grid"] + (meta["final_pos"] - meta["grid"]) * progress
                current_pos = max(1, round(current_pos))

                # Track position based on race progress
                track_progress = (lap_num % 1) if lap_num > 1 else 0
                spread = (1.0 - (current_pos - 1) * 0.03) % 1.0
                x, y = interpolate_track_position(track_points, spread)

                driver_frames.append(DriverFrame(
                    code=meta["code"],
                    position=current_pos,
                    x=round(x, 1),
                    y=round(y, 1),
                    speed=280 - (current_pos * 3),
                    team_color=meta["team_color"],
                    team_name=meta.get("team_name", ""),
                    track_progress=round(spread, 4),
                ))

            driver_frames.sort(key=lambda d: d.position)
            cumulative_time += 90.0
            frames.append(ReplayFrame(
                lap=lap_num,
                time_elapsed=round(cumulative_time, 1),
                drivers=driver_frames,
            ))
    else:
        for lap_num in sorted(laps_by_number.keys()):
            lap_list = laps_by_number[lap_num]
            driver_frames = []

            # Get leader time for gaps
            lap_times = [float(l.lap_time) for l in lap_list if l.lap_time and float(l.lap_time) > 0]
            leader_time = min(lap_times) if lap_times else 90.0

            for lap in lap_list:
                meta = ds_map.get(lap.driver_session_id)
                if not meta:
                    continue

                pos = lap.position or 20
                lt = float(lap.lap_time) if lap.lap_time and float(lap.lap_time) > 0 else 90.0
                gap = lt - leader_time

                # Place on track based on position (spread drivers around track)
                spread = (1.0 - (pos - 1) * 0.04) % 1.0
                x, y = interpolate_track_position(track_points, spread)

                driver_frames.append(DriverFrame(
                    code=meta["code"],
                    position=pos,
                    x=round(x, 1),
                    y=round(y, 1),
                    speed=round(280 - gap * 5, 1),
                    tyre=lap.tyre_compound or "",
                    tyre_age=lap.tyre_age or 0,
                    gap_to_leader=round(gap, 3),
                    team_color=meta["team_color"],
                    team_name=meta.get("team_name", ""),
                    lap_time=round(lt, 3) if lt < 300 else None,
                    track_progress=round(spread, 4),
                ))

            driver_frames.sort(key=lambda d: d.position)
            cumulative_time += leader_time
            frames.append(ReplayFrame(
                lap=lap_num,
                time_elapsed=round(cumulative_time, 1),
                drivers=driver_frames,
            ))

    return {
        "frames": [f.model_dump() for f in frames],
        "total_laps": session.total_laps or len(frames),
        "session_id": session_id,
    }


@router.get("/replay/{session_id}/events")
async def get_race_events(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get notable events: position changes, pit stops, DNFs"""
    events = []

    # Get position changes by comparing consecutive laps
    driver_sessions = db.query(DriverSession).join(Driver).filter(
        DriverSession.session_id == session_id
    ).all()

    for ds in driver_sessions:
        code = ds.driver.driver_code

        # DNF events
        if ds.dnf:
            events.append(RaceEvent(
                lap=0, time=0, type="dnf",
                driver=code,
                details=f"{code} retired: {ds.dnf_reason or ds.status or 'Retired'}"
            ))

        # Pit stops from lap data
        laps = db.query(Lap).filter(
            Lap.driver_session_id == ds.driver_session_id,
            Lap.pit_in_lap == True
        ).all()

        for lap in laps:
            events.append(RaceEvent(
                lap=lap.lap_number,
                time=lap.lap_number * 90.0,
                type="pit_stop",
                driver=code,
                details=f"{code} pit stop on lap {lap.lap_number}"
            ))

        # Overtakes (position improvements)
        all_laps = db.query(Lap).filter(
            Lap.driver_session_id == ds.driver_session_id,
            Lap.position.isnot(None)
        ).order_by(Lap.lap_number).all()

        for i in range(1, len(all_laps)):
            prev_pos = all_laps[i-1].position
            curr_pos = all_laps[i].position
            if prev_pos and curr_pos and curr_pos < prev_pos:
                gain = prev_pos - curr_pos
                if gain >= 2:  # Only report significant moves
                    events.append(RaceEvent(
                        lap=all_laps[i].lap_number,
                        time=all_laps[i].lap_number * 90.0,
                        type="overtake",
                        driver=code,
                        details=f"{code} gained {gain} positions (P{prev_pos} → P{curr_pos})"
                    ))

    events.sort(key=lambda e: e.lap)
    return {"events": [e.model_dump() for e in events]}


@router.get("/replay/{session_id}/weather")
async def get_session_weather(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get weather data for a session, grouped by lap"""
    weather_rows = db.query(Weather).filter(
        Weather.session_id == session_id
    ).order_by(Weather.lap_number).all()

    if not weather_rows:
        # Fallback: return typical weather based on the event location
        session_obj = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if session_obj:
            event = db.query(Event).filter(Event.event_id == session_obj.event_id).first()
            if event:
                typical = _get_typical_weather(event.event_name, event.country)
                return {"weather": typical, "by_lap": [], "source": "typical"}
        return {"weather": None}

    # Return the latest weather reading as session average
    latest = weather_rows[-1]
    air_temps = [float(w.air_temp) for w in weather_rows if w.air_temp]
    track_temps = [float(w.track_temp) for w in weather_rows if w.track_temp]
    humidities = [int(w.humidity) for w in weather_rows if w.humidity is not None]
    wind_speeds = [float(w.wind_speed) for w in weather_rows if w.wind_speed]
    has_rain = any(w.rainfall for w in weather_rows)

    return {
        "weather": {
            "air_temp": round(sum(air_temps) / len(air_temps), 1) if air_temps else None,
            "track_temp": round(sum(track_temps) / len(track_temps), 1) if track_temps else None,
            "humidity": round(sum(humidities) / len(humidities)) if humidities else None,
            "wind_speed": round(sum(wind_speeds) / len(wind_speeds), 1) if wind_speeds else None,
            "wind_direction": latest.wind_direction,
            "rainfall": has_rain,
            "pressure": float(latest.pressure) if latest.pressure else None,
            "conditions": "WET" if has_rain else "DRY",
        },
        "source": "live",
        "by_lap": [
            {
                "lap": w.lap_number,
                "air_temp": float(w.air_temp) if w.air_temp else None,
                "track_temp": float(w.track_temp) if w.track_temp else None,
                "humidity": int(w.humidity) if w.humidity is not None else None,
                "wind_speed": float(w.wind_speed) if w.wind_speed else None,
                "rainfall": w.rainfall or False,
            }
            for w in weather_rows
        ]
    }


# Typical weather data per circuit based on historical race-day averages
TYPICAL_WEATHER = {
    "bahrain": {"air_temp": 29.5, "track_temp": 38.2, "humidity": 42, "wind_speed": 15.3, "wind_direction": 310, "rainfall": False, "pressure": 1012.0, "conditions": "DRY"},
    "jeddah": {"air_temp": 30.1, "track_temp": 36.8, "humidity": 55, "wind_speed": 8.2, "wind_direction": 220, "rainfall": False, "pressure": 1011.0, "conditions": "DRY"},
    "australia": {"air_temp": 22.4, "track_temp": 32.1, "humidity": 48, "wind_speed": 12.5, "wind_direction": 195, "rainfall": False, "pressure": 1018.0, "conditions": "DRY"},
    "suzuka": {"air_temp": 24.8, "track_temp": 33.5, "humidity": 62, "wind_speed": 9.8, "wind_direction": 180, "rainfall": False, "pressure": 1015.0, "conditions": "DRY"},
    "shanghai": {"air_temp": 22.0, "track_temp": 30.5, "humidity": 58, "wind_speed": 11.2, "wind_direction": 150, "rainfall": False, "pressure": 1017.0, "conditions": "DRY"},
    "miami": {"air_temp": 31.2, "track_temp": 48.5, "humidity": 65, "wind_speed": 14.0, "wind_direction": 165, "rainfall": False, "pressure": 1014.0, "conditions": "DRY"},
    "imola": {"air_temp": 21.5, "track_temp": 35.8, "humidity": 52, "wind_speed": 7.5, "wind_direction": 270, "rainfall": False, "pressure": 1016.0, "conditions": "DRY"},
    "monaco": {"air_temp": 22.8, "track_temp": 41.2, "humidity": 50, "wind_speed": 4.5, "wind_direction": 200, "rainfall": False, "pressure": 1017.0, "conditions": "DRY"},
    "montreal": {"air_temp": 24.6, "track_temp": 39.0, "humidity": 55, "wind_speed": 10.8, "wind_direction": 240, "rainfall": False, "pressure": 1013.0, "conditions": "DRY"},
    "barcelona": {"air_temp": 27.3, "track_temp": 45.2, "humidity": 40, "wind_speed": 12.0, "wind_direction": 180, "rainfall": False, "pressure": 1016.0, "conditions": "DRY"},
    "austria": {"air_temp": 23.5, "track_temp": 38.0, "humidity": 42, "wind_speed": 8.5, "wind_direction": 290, "rainfall": False, "pressure": 1020.0, "conditions": "DRY"},
    "silverstone": {"air_temp": 20.8, "track_temp": 30.2, "humidity": 55, "wind_speed": 16.5, "wind_direction": 250, "rainfall": False, "pressure": 1012.0, "conditions": "DRY"},
    "hungary": {"air_temp": 31.0, "track_temp": 50.5, "humidity": 38, "wind_speed": 6.2, "wind_direction": 170, "rainfall": False, "pressure": 1015.0, "conditions": "DRY"},
    "spa": {"air_temp": 19.5, "track_temp": 27.8, "humidity": 65, "wind_speed": 11.0, "wind_direction": 260, "rainfall": False, "pressure": 1010.0, "conditions": "DRY"},
    "zandvoort": {"air_temp": 20.2, "track_temp": 28.5, "humidity": 62, "wind_speed": 18.5, "wind_direction": 280, "rainfall": False, "pressure": 1014.0, "conditions": "DRY"},
    "monza": {"air_temp": 28.5, "track_temp": 42.0, "humidity": 48, "wind_speed": 5.8, "wind_direction": 190, "rainfall": False, "pressure": 1015.0, "conditions": "DRY"},
    "baku": {"air_temp": 26.0, "track_temp": 40.5, "humidity": 50, "wind_speed": 12.8, "wind_direction": 320, "rainfall": False, "pressure": 1013.0, "conditions": "DRY"},
    "singapore": {"air_temp": 30.5, "track_temp": 33.8, "humidity": 72, "wind_speed": 3.2, "wind_direction": 140, "rainfall": False, "pressure": 1009.0, "conditions": "DRY"},
    "cota": {"air_temp": 27.8, "track_temp": 38.5, "humidity": 52, "wind_speed": 14.5, "wind_direction": 175, "rainfall": False, "pressure": 1014.0, "conditions": "DRY"},
    "mexico": {"air_temp": 22.5, "track_temp": 40.0, "humidity": 45, "wind_speed": 7.0, "wind_direction": 210, "rainfall": False, "pressure": 780.0, "conditions": "DRY"},
    "interlagos": {"air_temp": 25.2, "track_temp": 42.5, "humidity": 58, "wind_speed": 8.5, "wind_direction": 160, "rainfall": False, "pressure": 925.0, "conditions": "DRY"},
    "lasvegas": {"air_temp": 15.8, "track_temp": 14.2, "humidity": 25, "wind_speed": 10.5, "wind_direction": 300, "rainfall": False, "pressure": 1018.0, "conditions": "DRY"},
    "lusail": {"air_temp": 28.0, "track_temp": 30.5, "humidity": 55, "wind_speed": 12.0, "wind_direction": 340, "rainfall": False, "pressure": 1012.0, "conditions": "DRY"},
    "abudhabi": {"air_temp": 28.8, "track_temp": 32.0, "humidity": 58, "wind_speed": 8.0, "wind_direction": 300, "rainfall": False, "pressure": 1014.0, "conditions": "DRY"},
}


def _get_typical_weather(event_name: str, country: str) -> dict:
    """Return typical weather for a circuit based on event name / country."""
    name_lower = (event_name or "").lower()
    country_lower = (country or "").lower()

    # Map keywords to circuit keys
    mapping = {
        "bahrain": "bahrain", "sakhir": "bahrain",
        "saudi": "jeddah", "jeddah": "jeddah",
        "australia": "australia", "melbourne": "australia",
        "japan": "suzuka", "suzuka": "suzuka",
        "china": "shanghai", "shanghai": "shanghai",
        "miami": "miami",
        "emilia": "imola", "imola": "imola",
        "monaco": "monaco",
        "canada": "montreal", "montreal": "montreal",
        "spain": "barcelona", "barcelona": "barcelona",
        "austria": "austria", "spielberg": "austria",
        "britain": "silverstone", "silverstone": "silverstone",
        "hungary": "hungary", "budapest": "hungary",
        "belgium": "spa", "spa": "spa",
        "netherlands": "zandvoort", "zandvoort": "zandvoort",
        "monza": "monza",
        "azerbaijan": "baku", "baku": "baku",
        "singapore": "singapore",
        "united states": "cota", "austin": "cota",
        "mexico": "mexico",
        "brazil": "interlagos", "são paulo": "interlagos", "sao paulo": "interlagos",
        "las vegas": "lasvegas", "vegas": "lasvegas",
        "qatar": "lusail", "lusail": "lusail",
        "abu dhabi": "abudhabi",
    }

    # Check event name then country
    for keyword, circuit_key in sorted(mapping.items(), key=lambda x: -len(x[0])):
        if keyword in name_lower or keyword in country_lower:
            weather = TYPICAL_WEATHER.get(circuit_key)
            if weather:
                return weather

    # Generic fallback
    return {
        "air_temp": 25.0, "track_temp": 35.0, "humidity": 50,
        "wind_speed": 10.0, "wind_direction": 180, "rainfall": False,
        "pressure": 1013.0, "conditions": "DRY",
    }
