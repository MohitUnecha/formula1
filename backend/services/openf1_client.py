"""
OpenF1 API Client — Real-Time & Detailed Race Data Backup

Free-tier real-time F1 data API providing granular telemetry,
lap times, car data, team radio, intervals, and session info.

Base URL: https://api.openf1.org/v1/
Rate-limited — use as BACKUP only when FastF1/Jolpica data is unavailable.

Special features:
  - Team radio transcriptions (voice)
  - Car telemetry (speed, throttle, brake, gear, DRS)
  - Real-time position & interval data
  - Weather per-session
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openf1.org/v1"

# Rate limiting — be conservative with free tier
_RATE_LIMIT_DELAY = 0.5

# Cache
_cache: Dict[str, Tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(hours=1)


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and entry[1] > datetime.utcnow():
        return entry[0]
    return None


def _cache_set(key: str, value: Any):
    _cache[key] = (value, datetime.utcnow() + CACHE_TTL)


@dataclass
class OpenF1Session:
    session_key: int
    session_type: str
    session_name: str
    date_start: str
    date_end: str
    meeting_key: int
    circuit_key: int
    circuit_short_name: str
    country_name: str
    location: str
    year: int


@dataclass
class OpenF1Lap:
    """Lap data from OpenF1."""
    driver_number: int
    lap_number: int
    lap_duration: Optional[float] = None  # seconds
    is_pit_out_lap: bool = False
    duration_sector_1: Optional[float] = None
    duration_sector_2: Optional[float] = None
    duration_sector_3: Optional[float] = None
    st_speed: Optional[float] = None  # speed trap
    date_start: Optional[str] = None
    position: Optional[int] = None
    segments_sector_1: Optional[List[int]] = None
    segments_sector_2: Optional[List[int]] = None
    segments_sector_3: Optional[List[int]] = None


@dataclass
class OpenF1CarData:
    """High-frequency car telemetry sample."""
    driver_number: int
    date: str
    speed: int = 0
    throttle: int = 0
    brake: int = 0
    n_gear: int = 0
    rpm: int = 0
    drs: int = 0  # 0-14: DRS states


@dataclass
class OpenF1Position:
    """Position data at a point in time."""
    driver_number: int
    date: str
    position: int
    meeting_key: int
    session_key: int


@dataclass
class OpenF1Interval:
    """Gap data between drivers."""
    driver_number: int
    date: str
    gap_to_leader: Optional[float] = None
    interval: Optional[float] = None


@dataclass
class OpenF1TeamRadio:
    """Team radio message with recording URL."""
    driver_number: int
    date: str
    recording_url: str
    session_key: int
    meeting_key: int


@dataclass
class OpenF1Weather:
    """Weather data for a session."""
    date: str
    air_temperature: Optional[float] = None
    track_temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[int] = None
    rainfall: bool = False
    pressure: Optional[float] = None


@dataclass 
class OpenF1Driver:
    """Driver info from OpenF1."""
    driver_number: int
    broadcast_name: str
    full_name: str
    name_acronym: str
    team_name: str
    team_colour: str
    session_key: int
    country_code: Optional[str] = None
    headshot_url: Optional[str] = None


class OpenF1Client:
    """
    Async client for OpenF1 API.
    
    Usage:
        client = OpenF1Client()
        session = await client.find_session(2024, "Race", "Monza")
        laps = await client.get_laps(session.session_key, driver_number=44)
        radios = await client.get_team_radio(session.session_key)
    """

    def __init__(self, timeout: float = 20.0):
        self._timeout = timeout
        self._last_request = 0.0

    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make a GET request with caching and rate limiting."""
        cache_key = f"{endpoint}:{sorted(params.items()) if params else ''}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        import time
        now = time.monotonic()
        wait = _RATE_LIMIT_DELAY - (now - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)

        url = f"{BASE_URL}/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                self._last_request = time.monotonic()
                _cache_set(cache_key, data)
                return data
        except httpx.HTTPError as e:
            logger.error(f"OpenF1 API error: {e} — {url}")
            raise

    # ═══════════════════════════════════════════════════════════════════════
    # Sessions
    # ═══════════════════════════════════════════════════════════════════════

    async def find_session(
        self,
        year: int,
        session_type: str = "Race",
        circuit_short_name: Optional[str] = None,
        country_name: Optional[str] = None,
    ) -> Optional[OpenF1Session]:
        """Find a specific session by year, type, and circuit/country."""
        params: Dict[str, Any] = {"year": year, "session_type": session_type}
        if circuit_short_name:
            params["circuit_short_name"] = circuit_short_name
        if country_name:
            params["country_name"] = country_name
        
        data = await self._get("sessions", params)
        if not data:
            return None
        
        s = data[0]
        return OpenF1Session(
            session_key=s["session_key"],
            session_type=s["session_type"],
            session_name=s["session_name"],
            date_start=s["date_start"],
            date_end=s["date_end"],
            meeting_key=s["meeting_key"],
            circuit_key=s["circuit_key"],
            circuit_short_name=s["circuit_short_name"],
            country_name=s["country_name"],
            location=s["location"],
            year=s["year"],
        )

    async def get_sessions(self, year: int, session_type: Optional[str] = None) -> List[OpenF1Session]:
        """Get all sessions for a year (optionally filtered by type)."""
        params: Dict[str, Any] = {"year": year}
        if session_type:
            params["session_type"] = session_type
        
        data = await self._get("sessions", params)
        return [
            OpenF1Session(
                session_key=s["session_key"],
                session_type=s["session_type"],
                session_name=s["session_name"],
                date_start=s["date_start"],
                date_end=s["date_end"],
                meeting_key=s["meeting_key"],
                circuit_key=s["circuit_key"],
                circuit_short_name=s["circuit_short_name"],
                country_name=s["country_name"],
                location=s["location"],
                year=s["year"],
            )
            for s in data
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # Laps
    # ═══════════════════════════════════════════════════════════════════════

    async def get_laps(
        self,
        session_key: int,
        driver_number: Optional[int] = None,
        lap_number_lte: Optional[int] = None,
        lap_number_gte: Optional[int] = None,
    ) -> List[OpenF1Lap]:
        """Get lap data for a session, optionally filtered by driver/lap range."""
        params: Dict[str, Any] = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        if lap_number_lte:
            params["lap_number<="] = lap_number_lte
        if lap_number_gte:
            params["lap_number>="] = lap_number_gte
        
        data = await self._get("laps", params)
        return [
            OpenF1Lap(
                driver_number=l.get("driver_number", 0),
                lap_number=l.get("lap_number", 0),
                lap_duration=l.get("lap_duration"),
                is_pit_out_lap=l.get("is_pit_out_lap", False),
                duration_sector_1=l.get("duration_sector_1"),
                duration_sector_2=l.get("duration_sector_2"),
                duration_sector_3=l.get("duration_sector_3"),
                st_speed=l.get("st_speed"),
                date_start=l.get("date_start"),
                position=l.get("position"),
            )
            for l in data
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # Car Data (Telemetry)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_car_data(
        self,
        session_key: int,
        driver_number: Optional[int] = None,
        speed_gte: Optional[int] = None,
    ) -> List[OpenF1CarData]:
        """Get high-frequency car telemetry. WARNING: Very large datasets."""
        rows: List[dict] = []

        async def _fetch_for_driver(num: int) -> List[dict]:
            params: Dict[str, Any] = {
                "session_key": session_key,
                "driver_number": num,
            }
            if speed_gte:
                params["speed>="] = speed_gte
            return await self._get("car_data", params)

        if driver_number is not None:
            rows = await _fetch_for_driver(driver_number)
        else:
            # OpenF1 requires driver_number for car_data, so aggregate for all session drivers.
            drivers = await self.get_drivers(session_key)
            for d in drivers:
                try:
                    rows.extend(await _fetch_for_driver(d.driver_number))
                except Exception as e:
                    logger.debug("Skipping car data for driver %s: %s", d.driver_number, e)

        # Cap to prevent huge responses and keep response predictable.
        return [
            OpenF1CarData(
                driver_number=c.get("driver_number", 0),
                date=c.get("date", ""),
                speed=c.get("speed", 0),
                throttle=c.get("throttle", 0),
                brake=c.get("brake", 0),
                n_gear=c.get("n_gear", 0),
                rpm=c.get("rpm", 0),
                drs=c.get("drs", 0),
            )
            for c in rows[:5000]
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # Position & Intervals
    # ═══════════════════════════════════════════════════════════════════════

    async def get_positions(self, session_key: int, driver_number: Optional[int] = None) -> List[OpenF1Position]:
        """Get position data for a session."""
        params: Dict[str, Any] = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        data = await self._get("position", params)
        return [
            OpenF1Position(
                driver_number=p.get("driver_number", 0),
                date=p.get("date", ""),
                position=p.get("position", 0),
                meeting_key=p.get("meeting_key", 0),
                session_key=p.get("session_key", 0),
            )
            for p in data
        ]

    async def get_intervals(self, session_key: int, driver_number: Optional[int] = None) -> List[OpenF1Interval]:
        """Get interval/gap data between drivers."""
        params: Dict[str, Any] = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        data = await self._get("intervals", params)
        return [
            OpenF1Interval(
                driver_number=i.get("driver_number", 0),
                date=i.get("date", ""),
                gap_to_leader=i.get("gap_to_leader"),
                interval=i.get("interval"),
            )
            for i in data
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # Team Radio (Voice Feature)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_team_radio(
        self,
        session_key: int,
        driver_number: Optional[int] = None,
    ) -> List[OpenF1TeamRadio]:
        """
        Get team radio messages with recording URLs.
        This is the 'voice' feature — audio clips of driver-team communications.
        """
        params: Dict[str, Any] = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        
        data = await self._get("team_radio", params)
        return [
            OpenF1TeamRadio(
                driver_number=r.get("driver_number", 0),
                date=r.get("date", ""),
                recording_url=r.get("recording_url", ""),
                session_key=r.get("session_key", 0),
                meeting_key=r.get("meeting_key", 0),
            )
            for r in data
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # Weather
    # ═══════════════════════════════════════════════════════════════════════

    async def get_weather(self, session_key: int) -> List[OpenF1Weather]:
        """Get weather data for a session."""
        data = await self._get("weather", {"session_key": session_key})
        return [
            OpenF1Weather(
                date=w.get("date", ""),
                air_temperature=w.get("air_temperature"),
                track_temperature=w.get("track_temperature"),
                humidity=w.get("humidity"),
                wind_speed=w.get("wind_speed"),
                wind_direction=w.get("wind_direction"),
                rainfall=w.get("rainfall", False),
                pressure=w.get("pressure"),
            )
            for w in data
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # Drivers
    # ═══════════════════════════════════════════════════════════════════════

    async def get_drivers(self, session_key: int) -> List[OpenF1Driver]:
        """Get driver list for a session."""
        data = await self._get("drivers", {"session_key": session_key})
        return [
            OpenF1Driver(
                driver_number=d.get("driver_number", 0),
                broadcast_name=d.get("broadcast_name", ""),
                full_name=d.get("full_name", ""),
                name_acronym=d.get("name_acronym", ""),
                team_name=d.get("team_name", ""),
                team_colour=d.get("team_colour", ""),
                session_key=d.get("session_key", 0),
                country_code=d.get("country_code"),
                headshot_url=d.get("headshot_url"),
            )
            for d in data
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # Convenience: Prediction-Enhancing Data
    # ═══════════════════════════════════════════════════════════════════════

    async def get_session_summary(self, session_key: int) -> Dict:
        """
        Get a comprehensive summary of a session for prediction enhancement.
        Combines laps, weather, and intervals.
        """
        try:
            laps = await self.get_laps(session_key)
            weather = await self.get_weather(session_key)
            drivers = await self.get_drivers(session_key)
        except Exception as e:
            logger.warning(f"OpenF1 session summary failed: {e}")
            return {}

        # Aggregate lap data per driver
        driver_stats: Dict[int, Dict] = {}
        for lap in laps:
            dn = lap.driver_number
            if dn not in driver_stats:
                driver_stats[dn] = {"laps": [], "sectors": [], "speeds": []}
            if lap.lap_duration and lap.lap_duration > 0:
                driver_stats[dn]["laps"].append(lap.lap_duration)
            if lap.st_speed:
                driver_stats[dn]["speeds"].append(lap.st_speed)

        # Weather average
        avg_weather = {}
        if weather:
            air_temps = [w.air_temperature for w in weather if w.air_temperature]
            track_temps = [w.track_temperature for w in weather if w.track_temperature]
            avg_weather = {
                "avg_air_temp": sum(air_temps) / len(air_temps) if air_temps else None,
                "avg_track_temp": sum(track_temps) / len(track_temps) if track_temps else None,
                "had_rain": any(w.rainfall for w in weather),
            }

        # Driver name map
        driver_map = {d.driver_number: d.name_acronym for d in drivers}

        summary = {
            "session_key": session_key,
            "total_drivers": len(driver_stats),
            "weather": avg_weather,
            "drivers": {},
        }
        for dn, stats in driver_stats.items():
            code = driver_map.get(dn, str(dn))
            lap_times = stats["laps"]
            summary["drivers"][code] = {
                "total_laps": len(lap_times),
                "avg_lap": sum(lap_times) / len(lap_times) if lap_times else None,
                "best_lap": min(lap_times) if lap_times else None,
                "avg_speed_trap": sum(stats["speeds"]) / len(stats["speeds"]) if stats["speeds"] else None,
            }

        return summary

    async def get_team_radio_summary(self, session_key: int) -> Dict[str, List[str]]:
        """
        Get team radio recording URLs grouped by driver code.
        These can be used for audio playback in the frontend.
        """
        try:
            radios = await self.get_team_radio(session_key)
            drivers = await self.get_drivers(session_key)
        except Exception as e:
            logger.warning(f"Team radio fetch failed: {e}")
            return {}

        driver_map = {d.driver_number: d.name_acronym for d in drivers}
        result: Dict[str, List[str]] = {}
        for r in radios:
            code = driver_map.get(r.driver_number, str(r.driver_number))
            result.setdefault(code, []).append(r.recording_url)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════════════════════════
openf1 = OpenF1Client()
