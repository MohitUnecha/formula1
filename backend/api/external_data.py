"""
API Router: External Data

Exposes Jolpica-F1 and OpenF1 data as backup sources,
including team radio (voice) and enhanced prediction features.
Includes consolidated jolpica-f1 endpoint with fastf1 cross-reference.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from services.jolpica_client import jolpica
from services.openf1_client import openf1

logger = logging.getLogger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# Jolpica-F1 Consolidated Endpoint (with FastF1 cross-reference + disclaimers)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/jolpica-f1/{season}")
async def jolpica_f1_season_data(
    season: int,
    include_sprints: bool = True,
    include_standings: bool = True,
    include_schedule: bool = True,
):
    """
    Consolidated Jolpica-F1 endpoint — returns full season data with FastF1 cross-reference.
    
    NOTE: FastF1 detailed telemetry data (lap times, car telemetry, tyre data)
    is only available from 2018 onwards. For seasons before 2018, only basic
    race results from Jolpica are available without detailed telemetry.
    """
    data_disclaimer = None
    if season < 2018:
        data_disclaimer = (
            f"⚠️ FastF1 detailed telemetry (lap times, car data, tyre compounds) "
            f"is not available for the {season} season. Data shown is sourced from "
            f"Jolpica-F1 (Ergast replacement) and includes race results, standings, "
            f"and basic timing only. Detailed telemetry is available from 2018 onwards."
        )

    response = {
        "source": "jolpica-f1",
        "season": season,
        "data_disclaimer": data_disclaimer,
        "fastf1_telemetry_available": season >= 2018,
    }

    try:
        # Schedule
        if include_schedule:
            schedule = await jolpica.get_schedule(season)
            response["schedule"] = schedule
            response["total_rounds"] = len(schedule)

        # Race results
        results = await jolpica.get_race_results(season)
        response["race_results"] = [
            {
                "round": r.round,
                "race_name": r.race_name,
                "circuit_id": r.circuit_id,
                "circuit_name": r.circuit_name,
                "date": r.date,
                "driver_code": r.driver_code,
                "driver": f"{r.first_name} {r.last_name}",
                "position": r.position,
                "points": r.points,
                "grid": r.grid,
                "laps": r.laps,
                "status": r.status,
                "time": r.time_text,
                "fastest_lap": r.fastest_lap,
                "constructor": r.constructor_name,
            }
            for r in results
        ]
        response["total_race_results"] = len(results)

        # Sprint results
        if include_sprints:
            try:
                sprints = await jolpica.get_all_sprint_results(season)
                response["sprint_results"] = [
                    {
                        "round": r.round,
                        "race_name": r.race_name,
                        "driver_code": r.driver_code,
                        "driver": f"{r.first_name} {r.last_name}",
                        "position": r.position,
                        "points": r.points,
                        "grid": r.grid,
                        "constructor": r.constructor_name,
                    }
                    for r in sprints
                ]
                response["total_sprint_results"] = len(sprints)
            except Exception:
                response["sprint_results"] = []
                response["total_sprint_results"] = 0

        # Standings
        if include_standings:
            try:
                driver_standings = await jolpica.get_driver_standings(season)
                response["driver_standings"] = [
                    {
                        "position": s.position,
                        "driver_code": s.driver_code,
                        "driver": f"{s.first_name} {s.last_name}",
                        "points": s.points,
                        "wins": s.wins,
                        "constructor": s.constructor_name,
                        "nationality": s.nationality,
                    }
                    for s in driver_standings
                ]
            except Exception:
                response["driver_standings"] = []

            try:
                constructor_standings = await jolpica.get_constructor_standings(season)
                response["constructor_standings"] = [
                    {
                        "position": s.position,
                        "constructor": s.constructor_name,
                        "points": s.points,
                        "wins": s.wins,
                    }
                    for s in constructor_standings
                ]
            except Exception:
                response["constructor_standings"] = []

    except Exception as e:
        logger.error(f"Jolpica-F1 consolidated error: {e}")
        raise HTTPException(status_code=502, detail=f"Jolpica-F1 API error: {str(e)}")

    return response


@router.get("/jolpica-f1/{season}/{round_num}")
async def jolpica_f1_round_data(season: int, round_num: int):
    """
    Get comprehensive data for a specific round from Jolpica-F1.
    Includes race results, qualifying, pit stops, lap times, and sprint (if available).
    """
    data_disclaimer = None
    if season < 2018:
        data_disclaimer = (
            f"⚠️ FastF1 detailed telemetry is not available for {season}. "
            f"Data shown is from Jolpica-F1 only."
        )

    response = {
        "source": "jolpica-f1",
        "season": season,
        "round": round_num,
        "data_disclaimer": data_disclaimer,
        "fastf1_telemetry_available": season >= 2018,
    }

    try:
        # Race results
        results = await jolpica.get_race_results(season, round_num)
        response["race_results"] = [
            {
                "driver_code": r.driver_code,
                "driver": f"{r.first_name} {r.last_name}",
                "position": r.position,
                "points": r.points,
                "grid": r.grid,
                "laps": r.laps,
                "status": r.status,
                "time": r.time_text,
                "fastest_lap": r.fastest_lap,
                "constructor": r.constructor_name,
            }
            for r in results
        ]
        if results:
            response["race_name"] = results[0].race_name
            response["circuit"] = results[0].circuit_name

        # Qualifying
        try:
            quali = await jolpica.get_qualifying_results(season, round_num)
            response["qualifying"] = quali
        except Exception:
            response["qualifying"] = []

        # Sprint
        try:
            sprints = await jolpica.get_sprint_results(season, round_num)
            response["sprint_results"] = [
                {
                    "driver_code": r.driver_code,
                    "driver": f"{r.first_name} {r.last_name}",
                    "position": r.position,
                    "points": r.points,
                    "grid": r.grid,
                    "constructor": r.constructor_name,
                }
                for r in sprints
            ]
        except Exception:
            response["sprint_results"] = []

        # Pit stops
        try:
            pit_stops = await jolpica.get_pit_stops(season, round_num)
            response["pit_stops"] = [
                {
                    "driver_id": s.driver_id,
                    "lap": s.lap,
                    "stop": s.stop_number,
                    "duration": s.duration,
                }
                for s in pit_stops
            ]
        except Exception:
            response["pit_stops"] = []

        # Lap times (limit to prevent huge responses)
        try:
            laps = await jolpica.get_lap_times(season, round_num)
            response["lap_times"] = [
                {
                    "driver_id": l.driver_id,
                    "lap": l.lap_number,
                    "position": l.position,
                    "time": l.time_text,
                }
                for l in laps[:500]
            ]
            response["total_lap_entries"] = len(laps)
        except Exception:
            response["lap_times"] = []

    except Exception as e:
        logger.error(f"Jolpica-F1 round data error: {e}")
        raise HTTPException(status_code=502, detail=f"Jolpica-F1 API error: {str(e)}")

    return response


# ═══════════════════════════════════════════════════════════════════════════════
# Jolpica-F1 (Historical Backup)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/jolpica/results/{season}")
async def jolpica_season_results(season: int, round: Optional[int] = None):
    """Get race results from Jolpica-F1 API (Ergast replacement)."""
    try:
        results = await jolpica.get_race_results(season, round)
        return {
            "source": "jolpica-f1",
            "season": season,
            "total": len(results),
            "results": [
                {
                    "round": r.round,
                    "race_name": r.race_name,
                    "circuit": r.circuit_name,
                    "driver_code": r.driver_code,
                    "driver": f"{r.first_name} {r.last_name}",
                    "position": r.position,
                    "points": r.points,
                    "grid": r.grid,
                    "laps": r.laps,
                    "status": r.status,
                    "time": r.time_text,
                    "constructor": r.constructor_name,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Jolpica results error: {e}")
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


@router.get("/jolpica/sprints/{season}")
async def jolpica_sprint_results(season: int, round: Optional[int] = None):
    """Get sprint results from Jolpica-F1 API."""
    try:
        if round:
            results = await jolpica.get_sprint_results(season, round)
        else:
            results = await jolpica.get_all_sprint_results(season)
        return {
            "source": "jolpica-f1",
            "season": season,
            "total": len(results),
            "results": [
                {
                    "round": r.round,
                    "race_name": r.race_name,
                    "driver_code": r.driver_code,
                    "driver": f"{r.first_name} {r.last_name}",
                    "position": r.position,
                    "points": r.points,
                    "grid": r.grid,
                    "laps": r.laps,
                    "status": r.status,
                    "time": r.time_text,
                    "constructor": r.constructor_name,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Jolpica sprints error: {e}")
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


@router.get("/jolpica/standings/drivers/{season}")
async def jolpica_driver_standings(season: int):
    """Get driver standings from Jolpica-F1 API."""
    try:
        standings = await jolpica.get_driver_standings(season)
        return {
            "source": "jolpica-f1",
            "season": season,
            "standings": [
                {
                    "position": s.position,
                    "driver_code": s.driver_code,
                    "driver": f"{s.first_name} {s.last_name}",
                    "points": s.points,
                    "wins": s.wins,
                    "constructor": s.constructor_name,
                    "nationality": s.nationality,
                }
                for s in standings
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


@router.get("/jolpica/standings/constructors/{season}")
async def jolpica_constructor_standings(season: int):
    """Get constructor standings from Jolpica-F1 API."""
    try:
        standings = await jolpica.get_constructor_standings(season)
        return {
            "source": "jolpica-f1",
            "season": season,
            "standings": [
                {
                    "position": s.position,
                    "constructor": s.constructor_name,
                    "points": s.points,
                    "wins": s.wins,
                    "nationality": s.nationality,
                }
                for s in standings
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


@router.get("/jolpica/qualifying/{season}/{round}")
async def jolpica_qualifying(season: int, round: int):
    """Get qualifying results from Jolpica-F1 API."""
    try:
        results = await jolpica.get_qualifying_results(season, round)
        return {"source": "jolpica-f1", "season": season, "round": round, "results": results}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


@router.get("/jolpica/laps/{season}/{round}")
async def jolpica_laps(season: int, round: int, lap: Optional[int] = None):
    """Get lap-by-lap timing data from Jolpica-F1 API."""
    try:
        laps = await jolpica.get_lap_times(season, round, lap)
        return {
            "source": "jolpica-f1",
            "total": len(laps),
            "laps": [
                {
                    "driver_id": l.driver_id,
                    "lap": l.lap_number,
                    "position": l.position,
                    "time": l.time_text,
                    "time_millis": l.time_millis,
                }
                for l in laps
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


@router.get("/jolpica/pitstops/{season}/{round}")
async def jolpica_pitstops(season: int, round: int):
    """Get pit stop data from Jolpica-F1 API."""
    try:
        stops = await jolpica.get_pit_stops(season, round)
        return {
            "source": "jolpica-f1",
            "total": len(stops),
            "pit_stops": [
                {
                    "driver_id": s.driver_id,
                    "lap": s.lap,
                    "stop": s.stop_number,
                    "duration": s.duration,
                }
                for s in stops
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


@router.get("/jolpica/career/{driver_id}")
async def jolpica_career_stats(driver_id: str):
    """Get career stats for a driver from Jolpica-F1 API."""
    try:
        stats = await jolpica.get_driver_career_stats(driver_id)
        return {"source": "jolpica-f1", **stats}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


@router.get("/jolpica/circuit-history/{circuit_id}")
async def jolpica_circuit_history(circuit_id: str, limit: int = 10):
    """Get recent race results at a specific circuit."""
    try:
        results = await jolpica.get_circuit_history(circuit_id, limit)
        return {
            "source": "jolpica-f1",
            "circuit_id": circuit_id,
            "total": len(results),
            "results": [
                {
                    "season": r.season,
                    "round": r.round,
                    "driver_code": r.driver_code,
                    "position": r.position,
                    "grid": r.grid,
                    "status": r.status,
                    "constructor": r.constructor_name,
                }
                for r in results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jolpica API error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# OpenF1 (Real-Time Backup)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/openf1/sessions")
async def openf1_sessions(year: int, session_type: Optional[str] = None):
    """Get sessions from OpenF1 API."""
    try:
        sessions = await openf1.get_sessions(year, session_type)
        return {
            "source": "openf1",
            "total": len(sessions),
            "sessions": [
                {
                    "session_key": s.session_key,
                    "type": s.session_type,
                    "name": s.session_name,
                    "circuit": s.circuit_short_name,
                    "country": s.country_name,
                    "date": s.date_start,
                }
                for s in sessions
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")


@router.get("/openf1/laps/{session_key}")
async def openf1_laps(session_key: int, driver_number: Optional[int] = None):
    """Get lap data from OpenF1 API."""
    try:
        laps = await openf1.get_laps(session_key, driver_number)
        return {
            "source": "openf1",
            "total": len(laps),
            "laps": [
                {
                    "driver_number": l.driver_number,
                    "lap": l.lap_number,
                    "duration": l.lap_duration,
                    "position": l.position,
                    "sector_1": l.duration_sector_1,
                    "sector_2": l.duration_sector_2,
                    "sector_3": l.duration_sector_3,
                    "speed_trap": l.st_speed,
                    "pit_out": l.is_pit_out_lap,
                }
                for l in laps
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")


@router.get("/openf1/team-radio/{session_key}")
async def openf1_team_radio(session_key: int, driver_number: Optional[int] = None):
    """
    Get team radio recordings from OpenF1 API.
    Returns audio URLs for driver-team radio communications (voice feature).
    """
    try:
        radios = await openf1.get_team_radio(session_key, driver_number)
        return {
            "source": "openf1",
            "total": len(radios),
            "radios": [
                {
                    "driver_number": r.driver_number,
                    "date": r.date,
                    "recording_url": r.recording_url,
                }
                for r in radios
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")


@router.get("/openf1/team-radio-summary/{session_key}")
async def openf1_team_radio_summary(session_key: int):
    """
    Get team radio summary grouped by driver — useful for voice replay.
    """
    try:
        summary = await openf1.get_team_radio_summary(session_key)
        return {
            "source": "openf1",
            "drivers": {
                code: {"count": len(urls), "recordings": urls[:10]}
                for code, urls in summary.items()
            },
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")


@router.get("/openf1/weather/{session_key}")
async def openf1_weather(session_key: int):
    """Get weather data from OpenF1 API."""
    try:
        weather = await openf1.get_weather(session_key)
        return {
            "source": "openf1",
            "total": len(weather),
            "weather": [
                {
                    "date": w.date,
                    "air_temp": w.air_temperature,
                    "track_temp": w.track_temperature,
                    "humidity": w.humidity,
                    "wind_speed": w.wind_speed,
                    "wind_direction": w.wind_direction,
                    "rainfall": w.rainfall,
                }
                for w in weather
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")


@router.get("/openf1/session-summary/{session_key}")
async def openf1_session_summary(session_key: int):
    """
    Get comprehensive session summary from OpenF1 for prediction enhancement.
    Includes lap stats, weather averages, and speed trap data per driver.
    """
    try:
        summary = await openf1.get_session_summary(session_key)
        return {"source": "openf1", **summary}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")


@router.get("/openf1/car-data/{session_key}")
async def openf1_car_data(
    session_key: int,
    driver_number: Optional[int] = None,
):
    """
    Get car telemetry data from OpenF1 — speed, RPM, throttle, brake, gear, DRS.
    """
    try:
        data = await openf1.get_car_data(session_key, driver_number)
        return {
            "source": "openf1",
            "total": len(data),
            "car_data": [
                {
                    "driver_number": d.driver_number,
                    "speed": d.speed,
                    "rpm": d.rpm,
                    "throttle": d.throttle,
                    "brake": d.brake,
                    "gear": d.n_gear,
                    "drs": d.drs,
                    "date": d.date,
                }
                for d in data[:2000]  # limit to prevent huge responses
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")


@router.get("/openf1/positions/{session_key}")
async def openf1_positions(session_key: int):
    """
    Get position data from OpenF1 — driver positions over time during a session.
    """
    try:
        positions = await openf1.get_positions(session_key)
        return {
            "source": "openf1",
            "total": len(positions),
            "positions": [
                {
                    "driver_number": p.driver_number,
                    "position": p.position,
                    "date": p.date,
                }
                for p in positions
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")


@router.get("/openf1/intervals/{session_key}")
async def openf1_intervals(session_key: int):
    """
    Get interval/gap data from OpenF1 — gaps between cars during the race.
    """
    try:
        intervals = await openf1.get_intervals(session_key)
        return {
            "source": "openf1",
            "total": len(intervals),
            "intervals": [
                {
                    "driver_number": iv.driver_number,
                    "gap_to_leader": iv.gap_to_leader,
                    "interval": iv.interval,
                    "date": iv.date,
                }
                for iv in intervals[:2000]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenF1 API error: {str(e)}")
