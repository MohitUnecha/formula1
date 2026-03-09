"""
Jolpica-F1 API Client — Backup Historical Data Source

Ergast-compatible replacement for historical F1 data (1950–present).
Used as a backup when FastF1 doesn't have detailed results (pre-2018)
or when FastF1 data ingestion fails.

Base URL: https://api.jolpi.ca/ergast/f1/
Docs: https://github.com/jolpica/jolpica-f1

Provides:
  - Full race results with positions, times, status
  - Sprint results
  - Qualifying results
  - Driver & constructor standings
  - Circuit information
  - Lap-by-lap timing data
  - Pit stop data
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.jolpi.ca/ergast/f1"

# Rate limit: be polite — max ~4 req/s
_RATE_LIMIT_DELAY = 0.25

# In-memory cache (key → (data, expires_at))
_cache: Dict[str, Tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(hours=2)


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and entry[1] > datetime.utcnow():
        return entry[0]
    return None


def _cache_set(key: str, value: Any):
    _cache[key] = (value, datetime.utcnow() + CACHE_TTL)


@dataclass
class JolpicaRaceResult:
    """Parsed race/sprint result for a single driver."""
    season: int
    round: int
    race_name: str
    circuit_id: str
    circuit_name: str
    date: str
    driver_code: str
    driver_id: str
    first_name: str
    last_name: str
    driver_number: int
    position: int
    position_text: str
    points: float
    grid: int
    laps: int
    status: str
    time_millis: Optional[int] = None
    time_text: Optional[str] = None
    fastest_lap: Optional[str] = None
    fastest_lap_number: Optional[int] = None
    constructor_id: str = ""
    constructor_name: str = ""


@dataclass
class JolpicaStanding:
    """Driver or constructor standing."""
    position: int
    points: float
    wins: int
    driver_code: Optional[str] = None
    driver_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    constructor_id: Optional[str] = None
    constructor_name: Optional[str] = None
    nationality: Optional[str] = None


@dataclass
class JolpicaPitStop:
    """Pit stop data."""
    driver_code: str
    driver_id: str
    lap: int
    stop_number: int
    time_of_day: str
    duration: Optional[str] = None
    duration_millis: Optional[float] = None


@dataclass
class JolpicaLapTime:
    """Individual lap time."""
    driver_id: str
    lap_number: int
    position: int
    time_text: str
    time_millis: Optional[float] = None


class JolpicaF1Client:
    """
    Async client for Jolpica-F1 (Ergast-compatible) API.
    
    Usage:
        client = JolpicaF1Client()
        results = await client.get_race_results(2024, 1)
        standings = await client.get_driver_standings(2024)
    """

    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout
        self._last_request = 0.0

    async def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request with caching and rate limiting."""
        cache_key = f"{path}:{params}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        # Rate limiting
        import time
        now = time.monotonic()
        wait = _RATE_LIMIT_DELAY - (now - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)

        url = f"{BASE_URL}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                self._last_request = time.monotonic()
                _cache_set(cache_key, data)
                return data
        except httpx.HTTPError as e:
            logger.error(f"Jolpica API error: {e} — {url}")
            raise

    # ═══════════════════════════════════════════════════════════════════════
    # Race Results
    # ═══════════════════════════════════════════════════════════════════════

    async def get_race_results(self, season: int, round_num: Optional[int] = None) -> List[JolpicaRaceResult]:
        """Get race results for a season (all rounds) or a specific round."""
        path = f"/{season}/results.json" if round_num is None else f"/{season}/{round_num}/results.json"
        data = await self._get(path, {"limit": "1000"})
        
        results = []
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        for race in races:
            circuit = race.get("Circuit", {})
            for r in race.get("Results", []):
                driver = r.get("Driver", {})
                constructor = r.get("Constructor", {})
                time_data = r.get("Time", {})
                fl = r.get("FastestLap", {})
                results.append(JolpicaRaceResult(
                    season=int(race.get("season", season)),
                    round=int(race.get("round", 0)),
                    race_name=race.get("raceName", ""),
                    circuit_id=circuit.get("circuitId", ""),
                    circuit_name=circuit.get("circuitName", ""),
                    date=race.get("date", ""),
                    driver_code=driver.get("code", ""),
                    driver_id=driver.get("driverId", ""),
                    first_name=driver.get("givenName", ""),
                    last_name=driver.get("familyName", ""),
                    driver_number=int(r.get("number", 0)),
                    position=int(r.get("position", 0)),
                    position_text=r.get("positionText", ""),
                    points=float(r.get("points", 0)),
                    grid=int(r.get("grid", 0)),
                    laps=int(r.get("laps", 0)),
                    status=r.get("status", ""),
                    time_millis=int(time_data["millis"]) if "millis" in time_data else None,
                    time_text=time_data.get("time"),
                    fastest_lap=fl.get("Time", {}).get("time"),
                    fastest_lap_number=int(fl["lap"]) if "lap" in fl else None,
                    constructor_id=constructor.get("constructorId", ""),
                    constructor_name=constructor.get("name", ""),
                ))
        return results

    async def get_sprint_results(self, season: int, round_num: int) -> List[JolpicaRaceResult]:
        """Get sprint race results for a specific round."""
        path = f"/{season}/{round_num}/sprint.json"
        data = await self._get(path, {"limit": "1000"})
        
        results = []
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        for race in races:
            circuit = race.get("Circuit", {})
            for r in race.get("SprintResults", []):
                driver = r.get("Driver", {})
                constructor = r.get("Constructor", {})
                time_data = r.get("Time", {})
                fl = r.get("FastestLap", {})
                results.append(JolpicaRaceResult(
                    season=int(race.get("season", season)),
                    round=int(race.get("round", 0)),
                    race_name=race.get("raceName", ""),
                    circuit_id=circuit.get("circuitId", ""),
                    circuit_name=circuit.get("circuitName", ""),
                    date=race.get("date", ""),
                    driver_code=driver.get("code", ""),
                    driver_id=driver.get("driverId", ""),
                    first_name=driver.get("givenName", ""),
                    last_name=driver.get("familyName", ""),
                    driver_number=int(r.get("number", 0)),
                    position=int(r.get("position", 0)),
                    position_text=r.get("positionText", ""),
                    points=float(r.get("points", 0)),
                    grid=int(r.get("grid", 0)),
                    laps=int(r.get("laps", 0)),
                    status=r.get("status", ""),
                    time_millis=int(time_data["millis"]) if "millis" in time_data else None,
                    time_text=time_data.get("time"),
                    fastest_lap=fl.get("Time", {}).get("time"),
                    fastest_lap_number=int(fl["lap"]) if "lap" in fl else None,
                    constructor_id=constructor.get("constructorId", ""),
                    constructor_name=constructor.get("name", ""),
                ))
        return results

    async def get_all_sprint_results(self, season: int) -> List[JolpicaRaceResult]:
        """Get all sprint results for a full season."""
        path = f"/{season}/sprint.json"
        data = await self._get(path, {"limit": "1000"})
        
        results = []
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        for race in races:
            circuit = race.get("Circuit", {})
            for r in race.get("SprintResults", []):
                driver = r.get("Driver", {})
                constructor = r.get("Constructor", {})
                time_data = r.get("Time", {})
                fl = r.get("FastestLap", {})
                results.append(JolpicaRaceResult(
                    season=int(race.get("season", season)),
                    round=int(race.get("round", 0)),
                    race_name=race.get("raceName", ""),
                    circuit_id=circuit.get("circuitId", ""),
                    circuit_name=circuit.get("circuitName", ""),
                    date=race.get("date", ""),
                    driver_code=driver.get("code", ""),
                    driver_id=driver.get("driverId", ""),
                    first_name=driver.get("givenName", ""),
                    last_name=driver.get("familyName", ""),
                    driver_number=int(r.get("number", 0)),
                    position=int(r.get("position", 0)),
                    position_text=r.get("positionText", ""),
                    points=float(r.get("points", 0)),
                    grid=int(r.get("grid", 0)),
                    laps=int(r.get("laps", 0)),
                    status=r.get("status", ""),
                    time_millis=int(time_data["millis"]) if "millis" in time_data else None,
                    time_text=time_data.get("time"),
                    fastest_lap=fl.get("Time", {}).get("time"),
                    fastest_lap_number=int(fl["lap"]) if "lap" in fl else None,
                    constructor_id=constructor.get("constructorId", ""),
                    constructor_name=constructor.get("name", ""),
                ))
        return results

    # ═══════════════════════════════════════════════════════════════════════
    # Qualifying
    # ═══════════════════════════════════════════════════════════════════════

    async def get_qualifying_results(self, season: int, round_num: Optional[int] = None) -> List[Dict]:
        """Get qualifying results."""
        path = f"/{season}/qualifying.json" if round_num is None else f"/{season}/{round_num}/qualifying.json"
        data = await self._get(path, {"limit": "1000"})
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        results = []
        for race in races:
            for r in race.get("QualifyingResults", []):
                driver = r.get("Driver", {})
                constructor = r.get("Constructor", {})
                results.append({
                    "season": int(race.get("season", season)),
                    "round": int(race.get("round", 0)),
                    "driver_code": driver.get("code", ""),
                    "driver_id": driver.get("driverId", ""),
                    "first_name": driver.get("givenName", ""),
                    "last_name": driver.get("familyName", ""),
                    "position": int(r.get("position", 0)),
                    "constructor_id": constructor.get("constructorId", ""),
                    "constructor_name": constructor.get("name", ""),
                    "q1": r.get("Q1"),
                    "q2": r.get("Q2"),
                    "q3": r.get("Q3"),
                })
        return results

    # ═══════════════════════════════════════════════════════════════════════
    # Standings
    # ═══════════════════════════════════════════════════════════════════════

    async def get_driver_standings(self, season: int, round_num: Optional[int] = None) -> List[JolpicaStanding]:
        """Get driver standings for a season (after a specific round, or latest)."""
        if round_num:
            path = f"/{season}/{round_num}/driverStandings.json"
        else:
            path = f"/{season}/driverStandings.json"
        data = await self._get(path)
        
        standings = []
        lists = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
        for sl in lists:
            for ds in sl.get("DriverStandings", []):
                driver = ds.get("Driver", {})
                constructors = ds.get("Constructors", [])
                standings.append(JolpicaStanding(
                    position=int(ds.get("position", 0)),
                    points=float(ds.get("points", 0)),
                    wins=int(ds.get("wins", 0)),
                    driver_code=driver.get("code"),
                    driver_id=driver.get("driverId"),
                    first_name=driver.get("givenName"),
                    last_name=driver.get("familyName"),
                    nationality=driver.get("nationality"),
                    constructor_id=constructors[0].get("constructorId") if constructors else None,
                    constructor_name=constructors[0].get("name") if constructors else None,
                ))
        return standings

    async def get_constructor_standings(self, season: int) -> List[JolpicaStanding]:
        """Get constructor standings for a season."""
        data = await self._get(f"/{season}/constructorStandings.json")
        standings = []
        lists = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
        for sl in lists:
            for cs in sl.get("ConstructorStandings", []):
                constructor = cs.get("Constructor", {})
                standings.append(JolpicaStanding(
                    position=int(cs.get("position", 0)),
                    points=float(cs.get("points", 0)),
                    wins=int(cs.get("wins", 0)),
                    constructor_id=constructor.get("constructorId"),
                    constructor_name=constructor.get("name"),
                    nationality=constructor.get("nationality"),
                ))
        return standings

    # ═══════════════════════════════════════════════════════════════════════
    # Pit Stops
    # ═══════════════════════════════════════════════════════════════════════

    async def get_pit_stops(self, season: int, round_num: int) -> List[JolpicaPitStop]:
        """Get all pit stops for a specific race."""
        data = await self._get(f"/{season}/{round_num}/pitstops.json", {"limit": "1000"})
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        stops = []
        for race in races:
            for p in race.get("PitStops", []):
                dur_parts = p.get("duration", "0").split(":")
                try:
                    dur_ms = float(dur_parts[-1]) * 1000
                    if len(dur_parts) > 1:
                        dur_ms += int(dur_parts[-2]) * 60000
                except ValueError:
                    dur_ms = None
                stops.append(JolpicaPitStop(
                    driver_code="",  # Not in pit stop data — map via driver_id
                    driver_id=p.get("driverId", ""),
                    lap=int(p.get("lap", 0)),
                    stop_number=int(p.get("stop", 0)),
                    time_of_day=p.get("time", ""),
                    duration=p.get("duration"),
                    duration_millis=dur_ms,
                ))
        return stops

    # ═══════════════════════════════════════════════════════════════════════
    # Lap-by-Lap Timing
    # ═══════════════════════════════════════════════════════════════════════

    async def get_lap_times(self, season: int, round_num: int, lap: Optional[int] = None) -> List[JolpicaLapTime]:
        """Get lap times. If lap is None, gets all laps (paginated)."""
        if lap:
            data = await self._get(f"/{season}/{round_num}/laps/{lap}.json", {"limit": "1000"})
        else:
            data = await self._get(f"/{season}/{round_num}/laps.json", {"limit": "2000"})
        
        times = []
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        for race in races:
            for lap_data in race.get("Laps", []):
                lap_num = int(lap_data.get("number", 0))
                for t in lap_data.get("Timings", []):
                    # Parse "M:SS.mmm" → millis
                    time_str = t.get("time", "")
                    millis = None
                    if time_str:
                        try:
                            parts = time_str.split(":")
                            if len(parts) == 2:
                                millis = int(parts[0]) * 60000 + float(parts[1]) * 1000
                            else:
                                millis = float(parts[0]) * 1000
                        except ValueError:
                            pass
                    times.append(JolpicaLapTime(
                        driver_id=t.get("driverId", ""),
                        lap_number=lap_num,
                        position=int(t.get("position", 0)),
                        time_text=time_str,
                        time_millis=millis,
                    ))
        return times

    # ═══════════════════════════════════════════════════════════════════════
    # Circuits & Schedule
    # ═══════════════════════════════════════════════════════════════════════

    async def get_schedule(self, season: int) -> List[Dict]:
        """Get full season schedule with circuit info."""
        data = await self._get(f"/{season}.json", {"limit": "30"})
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        schedule = []
        for race in races:
            circuit = race.get("Circuit", {})
            loc = circuit.get("Location", {})
            schedule.append({
                "season": int(race.get("season", season)),
                "round": int(race.get("round", 0)),
                "race_name": race.get("raceName", ""),
                "circuit_id": circuit.get("circuitId", ""),
                "circuit_name": circuit.get("circuitName", ""),
                "date": race.get("date", ""),
                "time": race.get("time"),
                "country": loc.get("country", ""),
                "locality": loc.get("locality", ""),
                "lat": loc.get("lat"),
                "lng": loc.get("long"),
            })
        return schedule

    async def get_circuits(self) -> List[Dict]:
        """Get all circuits."""
        data = await self._get("/circuits.json", {"limit": "100"})
        circuits = data.get("MRData", {}).get("CircuitTable", {}).get("Circuits", [])
        return [
            {
                "circuit_id": c.get("circuitId", ""),
                "circuit_name": c.get("circuitName", ""),
                "country": c.get("Location", {}).get("country", ""),
                "locality": c.get("Location", {}).get("locality", ""),
                "lat": c.get("Location", {}).get("lat"),
                "lng": c.get("Location", {}).get("long"),
            }
            for c in circuits
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # Convenience: Historical Performance Features
    # ═══════════════════════════════════════════════════════════════════════

    async def get_driver_career_stats(self, driver_id: str) -> Dict:
        """Get lifetime career stats for a driver from Jolpica API."""
        data = await self._get(f"/drivers/{driver_id}/results.json", {"limit": "1000"})
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])

        wins = 0
        podiums = 0
        poles = 0
        dnfs = 0
        total = 0
        total_points = 0.0
        positions = []

        for race in races:
            for r in race.get("Results", []):
                total += 1
                pos = int(r.get("position", 0))
                positions.append(pos)
                total_points += float(r.get("points", 0))
                if pos == 1:
                    wins += 1
                if pos <= 3:
                    podiums += 1
                if int(r.get("grid", 0)) == 1:
                    poles += 1
                status = r.get("status", "")
                if status and status != "Finished" and not status.startswith("+"):
                    dnfs += 1

        return {
            "driver_id": driver_id,
            "races": total,
            "wins": wins,
            "podiums": podiums,
            "poles": poles,
            "dnfs": dnfs,
            "total_points": total_points,
            "avg_position": sum(positions) / len(positions) if positions else None,
            "win_rate": wins / total if total else 0,
            "podium_rate": podiums / total if total else 0,
            "dnf_rate": dnfs / total if total else 0,
        }

    async def get_circuit_history(self, circuit_id: str, limit: int = 10) -> List[JolpicaRaceResult]:
        """Get recent race results at a specific circuit (for circuit-specific prediction features)."""
        data = await self._get(f"/circuits/{circuit_id}/results.json", {"limit": str(limit * 20)})
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])

        results = []
        for race in races[-limit:]:
            circuit = race.get("Circuit", {})
            for r in race.get("Results", []):
                driver = r.get("Driver", {})
                constructor = r.get("Constructor", {})
                time_data = r.get("Time", {})
                results.append(JolpicaRaceResult(
                    season=int(race.get("season", 0)),
                    round=int(race.get("round", 0)),
                    race_name=race.get("raceName", ""),
                    circuit_id=circuit.get("circuitId", ""),
                    circuit_name=circuit.get("circuitName", ""),
                    date=race.get("date", ""),
                    driver_code=driver.get("code", ""),
                    driver_id=driver.get("driverId", ""),
                    first_name=driver.get("givenName", ""),
                    last_name=driver.get("familyName", ""),
                    driver_number=int(r.get("number", 0)),
                    position=int(r.get("position", 0)),
                    position_text=r.get("positionText", ""),
                    points=float(r.get("points", 0)),
                    grid=int(r.get("grid", 0)),
                    laps=int(r.get("laps", 0)),
                    status=r.get("status", ""),
                    time_millis=int(time_data["millis"]) if "millis" in time_data else None,
                    time_text=time_data.get("time"),
                    constructor_id=constructor.get("constructorId", ""),
                    constructor_name=constructor.get("name", ""),
                ))
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════════════════════════
jolpica = JolpicaF1Client()
