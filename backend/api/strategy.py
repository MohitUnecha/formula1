"""
API Router: Strategy Predictions

Circuit-specific tyre strategy and pit stop predictions based on historical data.
Analyzes actual race data (Lap table: tyre_compound, tyre_age, pit_in_lap) to predict:
    - Most likely tyre compound per team
    - Pit stop windows (which lap each driver is likely to pit)
    - Stint lengths per compound
    - Overall circuit tyre profile
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, case
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from collections import defaultdict
import logging
import math

from database import get_db
from models import (
    Lap, DriverSession, Session as DBSession, Event, Driver
)
from team_mapping import get_team_for_driver

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class StintInfo(BaseModel):
    compound: str
    avg_laps: float
    median_laps: float
    min_laps: int
    max_laps: int
    pit_lap: Optional[int] = None  # average lap to pit after this stint

class DriverStrategy(BaseModel):
    driver_code: str
    driver_name: str
    team: str
    team_color: str
    predicted_stops: int
    predicted_stints: List[StintInfo]
    pit_laps: List[int]  # predicted lap numbers for pit stops
    confidence: str  # high / medium / low

class TeamCompound(BaseModel):
    team: str
    team_color: str
    drivers: List[str]
    most_likely_start: str  # compound they'll start on
    start_probability: float
    most_likely_strategy: str  # e.g. "MEDIUM → HARD"
    strategy_probability: float
    compound_distribution: Dict[str, float]  # compound -> % of total laps

class CircuitProfile(BaseModel):
    circuit_name: str
    total_laps: int
    avg_pit_stops: float
    historical_races_analyzed: int
    compound_usage: Dict[str, float]  # compound -> % of total laps
    avg_stint_lengths: Dict[str, float]  # compound -> avg stint length
    degradation_rates: Dict[str, float]  # compound -> estimated deg %/lap
    typical_pit_windows: List[Dict[str, Any]]  # [{window_start, window_end, stop_number}]

class StrategyResponse(BaseModel):
    circuit_profile: CircuitProfile
    team_compounds: List[TeamCompound]
    driver_strategies: List[DriverStrategy]
    data_quality: str  # 'rich' | 'moderate' | 'limited' | 'no_data'


# ═══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

# Team color mapping
TEAM_COLORS: Dict[str, str] = {
    'Red Bull Racing': '#3671C6', 'Red Bull': '#3671C6',
    'Ferrari': '#E8002D', 'Scuderia Ferrari': '#E8002D',
    'Mercedes': '#27F4D2', 'Mercedes-AMG': '#27F4D2',
    'McLaren': '#FF8000',
    'Aston Martin': '#229971',
    'Alpine': '#FF87BC', 'Alpine F1 Team': '#FF87BC',
    'Williams': '#64C4FF',
    'Haas F1 Team': '#B6BABD', 'Haas': '#B6BABD',
    'Kick Sauber': '#52E252', 'Sauber': '#52E252',
    'RB': '#6692FF', 'Racing Bulls': '#6692FF', 'Visa Cash App RB': '#6692FF',
    'Cadillac': '#1E3A5F',
}

def get_team_color(team_name: str) -> str:
    if not team_name:
        return '#888888'
    for key, color in TEAM_COLORS.items():
        if key.lower() in team_name.lower():
            return color
    return '#888888'


def detect_stints(laps: list) -> list:
    """
    Detect stints from a sequence of laps (ordered by lap_number).
    A new stint starts when tyre_compound changes or tyre_age resets.
    Returns list of dicts: [{compound, start_lap, end_lap, laps, pit_lap}]
    """
    if not laps:
        return []

    stints = []
    current_compound = None
    start_lap = None
    prev_age = None

    for lap in laps:
        compound = lap.tyre_compound
        age = lap.tyre_age

        if compound is None or compound in ('None', 'nan', 'UNKNOWN', ''):
            continue

        # Detect stint change: compound changed or tyre_age reset
        new_stint = False
        if current_compound is None:
            new_stint = True
        elif compound != current_compound:
            new_stint = True
        elif prev_age is not None and age is not None and age < prev_age - 1:
            new_stint = True

        if new_stint:
            if current_compound is not None and start_lap is not None:
                stints.append({
                    'compound': current_compound,
                    'start_lap': start_lap,
                    'end_lap': lap.lap_number - 1,
                    'laps': lap.lap_number - start_lap,
                    'pit_lap': lap.lap_number - 1,  # pitted at end of previous stint
                })
            current_compound = compound
            start_lap = lap.lap_number

        prev_age = age

    # Final stint (no pit at end)
    if current_compound and start_lap:
        last_lap = laps[-1].lap_number if laps else start_lap
        stints.append({
            'compound': current_compound,
            'start_lap': start_lap,
            'end_lap': last_lap,
            'laps': last_lap - start_lap + 1,
            'pit_lap': None,
        })

    return stints


def estimate_degradation(laps: list, compound: str) -> float:
    """
    Estimate tyre degradation rate (%/lap) from lap time progression.
    Uses lap times at different tyre ages to compute trend.
    """
    compound_laps = [
        l for l in laps
        if l.tyre_compound == compound
        and l.lap_time is not None
        and float(l.lap_time) > 0
        and float(l.lap_time) < 300
        and l.tyre_age is not None
        and l.tyre_age >= 3
    ]

    defaults = {'SOFT': 1.6, 'MEDIUM': 1.0, 'HARD': 0.6, 'INTERMEDIATE': 1.2, 'WET': 0.8}

    if len(compound_laps) < 10:
        # Default degradation rates
        defaults = {'SOFT': 1.6, 'MEDIUM': 1.0, 'HARD': 0.6, 'INTERMEDIATE': 1.2, 'WET': 0.8}
        return defaults.get(compound, 1.0)

    # Group by tyre_age and compute average lap time per age
    age_times: Dict[int, list] = defaultdict(list)
    for l in compound_laps:
        age_times[l.tyre_age].append(float(l.lap_time))

    ages = sorted(age_times.keys())
    if len(ages) < 3:
        defaults = {'SOFT': 1.6, 'MEDIUM': 1.0, 'HARD': 0.6, 'INTERMEDIATE': 1.2, 'WET': 0.8}
        return defaults.get(compound, 1.0)

    # Simple linear regression: time vs age
    avg_times = [(age, sum(age_times[age]) / len(age_times[age])) for age in ages]
    base_time = avg_times[0][1]
    if base_time <= 0:
        return 1.0

    # Compute average degradation per lap as % of base time
    total_deg = 0
    count = 0
    for age, t in avg_times[1:]:
        deg_pct = ((t - base_time) / base_time) * 100 / max(age - ages[0], 1)
        total_deg += deg_pct
        count += 1

    if count == 0:
        return defaults.get(compound, 1.0)

    computed = total_deg / count
    # If computed value is too low (data noise), use weighted blend with defaults
    default_val = defaults.get(compound, 1.0)
    if computed < 0.2:
        return default_val
    return round(max(0.3, min(computed, 3.0)), 2)


def median(values: list) -> float:
    if not values:
        return 0
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy Prediction Endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/strategy", response_model=StrategyResponse)
def get_strategy_prediction(
    season: int = Query(..., ge=2018, le=2030),
    race_round: int = Query(..., alias="round", ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Predict tyre strategy for a specific race based on historical data.
    
    Analyzes past races at the same circuit to predict:
    - Most likely compound choices per team
    - Pit stop windows
    - Stint lengths
    """

    # ── 1. Find the target event and its circuit
    target_event = db.query(Event).filter(
        Event.season == season,
        Event.round == race_round
    ).first()

    if not target_event:
        return _build_no_data_response(f"Round {round} {season}")

    circuit_name = target_event.event_name
    circuit_key = target_event.circuit_key

    # ── 2. Find all historical race sessions at this circuit
    # Match by event_name pattern (e.g., "Abu Dhabi Grand Prix")
    # Also try circuit_key if available
    name_pattern = _extract_circuit_pattern(circuit_name)

    historical_events = db.query(Event).filter(
        Event.event_name.contains(name_pattern),
        Event.season <= season
    ).order_by(Event.season.desc()).all()

    if circuit_key:
        # Also match by circuit_key
        extra = db.query(Event).filter(
            Event.circuit_key == circuit_key,
            Event.season <= season
        ).order_by(Event.season.desc()).all()
        seen = {e.event_id for e in historical_events}
        for e in extra:
            if e.event_id not in seen:
                historical_events.append(e)

    # Filter to recent era only (2019+ uses current SOFT/MEDIUM/HARD system)
    # For older seasons, include their data but for 2022+ only use modern data
    min_season = max(2019, season - 5)  # Only look back 5 years max from current era
    historical_events = [e for e in historical_events if e.season >= min_season]

    if not historical_events:
        return _build_no_data_response(circuit_name)

    # ── 3. Get all race sessions for these events
    event_ids = [e.event_id for e in historical_events]
    race_sessions = db.query(DBSession).filter(
        DBSession.event_id.in_(event_ids),
        DBSession.session_type == 'R'
    ).all()

    if not race_sessions:
        return _build_no_data_response(circuit_name)

    session_ids = [s.session_id for s in race_sessions]
    total_race_laps = race_sessions[0].total_laps or 58  # fallback

    # For the target season, try to get the exact total_laps
    target_session = None
    for s in race_sessions:
        evt = next((e for e in historical_events if e.event_id == s.event_id and e.season == season), None)
        if evt:
            target_session = s
            total_race_laps = s.total_laps or total_race_laps
            break

    # ── 4. Get all driver sessions and laps for these races
    driver_sessions = db.query(DriverSession, Driver).join(Driver).filter(
        DriverSession.session_id.in_(session_ids)
    ).all()

    if not driver_sessions:
        return _build_no_data_response(circuit_name)

    # Group driver sessions by session
    ds_by_session: Dict[int, list] = defaultdict(list)
    for ds, drv in driver_sessions:
        ds_by_session[ds.session_id].append((ds, drv))

    # ── 5. Analyze all historical stints
    all_stints = []  # All stints across all historical races
    driver_stints: Dict[str, list] = defaultdict(list)  # driver_code -> [stints per race]
    team_stints: Dict[str, list] = defaultdict(list)  # team -> [stints per race]
    compound_laps: Dict[str, list] = defaultdict(list)  # compound -> [lap counts per stint]
    all_laps_for_deg = []  # For degradation estimation

    for session_id in session_ids:
        for ds, drv in ds_by_session.get(session_id, []):
            # Get laps for this driver session
            laps = db.query(Lap).filter(
                Lap.driver_session_id == ds.driver_session_id
            ).order_by(Lap.lap_number).all()

            if not laps or len(laps) < 5:
                continue

            all_laps_for_deg.extend(laps)

            stints = detect_stints(laps)
            if not stints:
                continue

            all_stints.append(stints)

            # Get team for driver
            team_info = get_team_for_driver(drv.driver_code, season)
            team = team_info[0] if team_info else (drv.team_name or 'Unknown')

            driver_stints[drv.driver_code].append(stints)
            team_stints[team].append(stints)

            for stint in stints:
                compound_laps[stint['compound']].append(stint['laps'])

    if not all_stints:
        return _build_no_data_response(circuit_name)

    # ── 6. Build circuit profile
    total_compound_laps = defaultdict(int)
    for stint_list in all_stints:
        for stint in stint_list:
            total_compound_laps[stint['compound']] += stint['laps']

    grand_total = sum(total_compound_laps.values()) or 1

    compound_usage = {
        comp: round(laps / grand_total * 100, 1)
        for comp, laps in sorted(total_compound_laps.items(), key=lambda x: -x[1])
    }

    avg_stint_lengths = {
        comp: round(sum(lengths) / len(lengths), 1)
        for comp, lengths in compound_laps.items()
        if lengths
    }

    # Degradation rates
    degradation_rates = {}
    for compound in compound_laps:
        degradation_rates[compound] = estimate_degradation(all_laps_for_deg, compound)

    # Pit windows - analyze when pits typically happen
    all_pit_laps: Dict[int, list] = defaultdict(list)  # stop_number -> [pit_laps]
    for stint_list in all_stints:
        for i, stint in enumerate(stint_list):
            if stint['pit_lap'] is not None and i < len(stint_list) - 1:
                all_pit_laps[i + 1].append(stint['pit_lap'])

    typical_pit_windows = []
    for stop_num in sorted(all_pit_laps.keys()):
        pit_laps_list = all_pit_laps[stop_num]
        if pit_laps_list:
            avg = sum(pit_laps_list) / len(pit_laps_list)
            std = math.sqrt(sum((x - avg) ** 2 for x in pit_laps_list) / len(pit_laps_list)) if len(pit_laps_list) > 1 else 3
            typical_pit_windows.append({
                'stop_number': stop_num,
                'window_start': max(1, int(avg - std)),
                'window_end': min(total_race_laps, int(avg + std)),
                'avg_lap': round(avg, 1),
                'samples': len(pit_laps_list),
            })

    # Average pit stops per race
    pit_counts = [len([s for s in stint_list if s['pit_lap'] is not None]) for stint_list in all_stints]
    avg_pit_stops = sum(pit_counts) / len(pit_counts) if pit_counts else 1.5

    circuit_profile = CircuitProfile(
        circuit_name=circuit_name,
        total_laps=total_race_laps,
        avg_pit_stops=round(avg_pit_stops, 1),
        historical_races_analyzed=len(race_sessions),
        compound_usage=compound_usage,
        avg_stint_lengths=avg_stint_lengths,
        degradation_rates=degradation_rates,
        typical_pit_windows=typical_pit_windows,
    )

    # ── 7. Team compound predictions
    team_compound_list = []
    for team, races_stints in team_stints.items():
        if not races_stints:
            continue

        # Starting compound distribution
        start_compounds: Dict[str, int] = defaultdict(int)
        strategy_patterns: Dict[str, int] = defaultdict(int)
        total_team_laps: Dict[str, int] = defaultdict(int)
        team_drivers = set()

        for stint_list in races_stints:
            if stint_list:
                start_compounds[stint_list[0]['compound']] += 1

                # Strategy pattern (e.g., "MEDIUM → HARD")
                pattern = ' → '.join(s['compound'] for s in stint_list)
                strategy_patterns[pattern] += 1

                for stint in stint_list:
                    total_team_laps[stint['compound']] += stint['laps']

        total_starts = sum(start_compounds.values()) or 1
        most_likely_start = max(start_compounds, key=start_compounds.get)
        start_prob = start_compounds[most_likely_start] / total_starts

        total_strategies = sum(strategy_patterns.values()) or 1
        most_likely_strategy = max(strategy_patterns, key=strategy_patterns.get)
        strategy_prob = strategy_patterns[most_likely_strategy] / total_strategies

        total_tl = sum(total_team_laps.values()) or 1
        compound_dist = {c: round(l / total_tl * 100, 1) for c, l in total_team_laps.items()}

        # Find drivers on this team for current season
        drivers_on_team = set()
        for ds, drv in driver_sessions:
            t_info = get_team_for_driver(drv.driver_code, season)
            t = t_info[0] if t_info else (drv.team_name or 'Unknown')
            if t == team:
                drivers_on_team.add(drv.driver_code)

        team_compound_list.append(TeamCompound(
            team=team,
            team_color=get_team_color(team),
            drivers=sorted(drivers_on_team)[:2],
            most_likely_start=most_likely_start,
            start_probability=round(start_prob, 2),
            most_likely_strategy=most_likely_strategy,
            strategy_probability=round(strategy_prob, 2),
            compound_distribution=compound_dist,
        ))

    # Sort by strategy probability
    team_compound_list.sort(key=lambda x: -x.strategy_probability)

    # ── 8. Driver strategy predictions
    driver_strategy_list = []

    # Get current drivers (from most recent session)
    latest_session_id = max(session_ids) if session_ids else None
    current_drivers = []
    if latest_session_id:
        current_drivers = [
            (ds, drv) for ds, drv in ds_by_session.get(latest_session_id, [])
        ]

    # If no current drivers, try to use any available
    if not current_drivers:
        for sid in sorted(session_ids, reverse=True):
            if ds_by_session.get(sid):
                current_drivers = ds_by_session[sid]
                break

    for ds, drv in current_drivers:
        team_info = get_team_for_driver(drv.driver_code, season)
        team = team_info[0] if team_info else (drv.team_name or 'Unknown')

        # Use driver's own historical stints if available, else team average
        drv_stints = driver_stints.get(drv.driver_code, [])

        if drv_stints:
            # Use driver's own data
            source_stints = drv_stints
        elif team in team_stints:
            # Fallback to team data
            source_stints = team_stints[team]
        else:
            # Generic circuit data
            source_stints = all_stints[:5]

        if not source_stints:
            continue

        # Predict number of stops
        stop_counts = [len([s for s in sl if s['pit_lap'] is not None]) for sl in source_stints]
        predicted_stops = round(sum(stop_counts) / len(stop_counts)) if stop_counts else 1

        # Build predicted stints
        # Use most common stint pattern
        patterns = defaultdict(int)
        for sl in source_stints:
            pattern = tuple(s['compound'] for s in sl)
            patterns[pattern] += 1

        best_pattern = max(patterns, key=patterns.get) if patterns else ('MEDIUM', 'HARD')

        # Calculate avg stint lengths for each position in the pattern
        predicted_stints = []
        predicted_pit_laps = []

        for stint_idx, compound in enumerate(best_pattern):
            # Get all stint lengths at this position with this compound
            lengths = []
            pit_laps = []
            for sl in source_stints:
                if stint_idx < len(sl) and sl[stint_idx]['compound'] == compound:
                    lengths.append(sl[stint_idx]['laps'])
                    if sl[stint_idx]['pit_lap'] is not None:
                        pit_laps.append(sl[stint_idx]['pit_lap'])

            if not lengths:
                # Fallback to general compound data
                lengths = compound_laps.get(compound, [20])

            avg_l = sum(lengths) / len(lengths) if lengths else 20
            med_l = median(lengths)

            stint_info = StintInfo(
                compound=compound,
                avg_laps=round(avg_l, 1),
                median_laps=round(med_l, 1),
                min_laps=min(lengths) if lengths else 10,
                max_laps=max(lengths) if lengths else 30,
                pit_lap=round(sum(pit_laps) / len(pit_laps)) if pit_laps else None,
            )
            predicted_stints.append(stint_info)

            if pit_laps:
                predicted_pit_laps.append(round(sum(pit_laps) / len(pit_laps)))

        # Confidence based on data quantity
        data_points = len(source_stints)
        confidence = 'high' if data_points >= 4 else 'medium' if data_points >= 2 else 'low'

        driver_name = f"{drv.first_name} {drv.last_name}" if drv.first_name else drv.driver_code

        driver_strategy_list.append(DriverStrategy(
            driver_code=drv.driver_code,
            driver_name=driver_name,
            team=team,
            team_color=get_team_color(team),
            predicted_stops=predicted_stops,
            predicted_stints=predicted_stints,
            pit_laps=predicted_pit_laps,
            confidence=confidence,
        ))

    # Sort by position if available, else alphabetically
    driver_strategy_list.sort(key=lambda x: x.driver_code)

    # Data quality assessment
    total_data_points = sum(len(sl) for sl in all_stints)
    data_quality = (
        'rich' if total_data_points > 100 else
        'moderate' if total_data_points > 30 else
        'limited' if total_data_points > 0 else
        'no_data'
    )

    return StrategyResponse(
        circuit_profile=circuit_profile,
        team_compounds=team_compound_list,
        driver_strategies=driver_strategy_list,
        data_quality=data_quality,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_circuit_pattern(event_name: str) -> str:
    """Extract the core circuit name for matching across years."""
    # "Abu Dhabi Grand Prix" -> "Abu Dhabi"
    # "British Grand Prix" -> "British"
    name = event_name.replace('Grand Prix', '').strip()
    # Remove common suffixes
    for suffix in ['GP', 'Prix', 'Race']:
        name = name.replace(suffix, '').strip()
    return name


def _build_no_data_response(circuit_name: str) -> StrategyResponse:
    """Return a response with sensible defaults when no data is available."""
    return StrategyResponse(
        circuit_profile=CircuitProfile(
            circuit_name=circuit_name,
            total_laps=56,
            avg_pit_stops=1.5,
            historical_races_analyzed=0,
            compound_usage={'HARD': 45, 'MEDIUM': 35, 'SOFT': 20},
            avg_stint_lengths={'HARD': 28, 'MEDIUM': 22, 'SOFT': 14},
            degradation_rates={'SOFT': 1.6, 'MEDIUM': 1.0, 'HARD': 0.6},
            typical_pit_windows=[
                {'stop_number': 1, 'window_start': 15, 'window_end': 25, 'avg_lap': 20, 'samples': 0}
            ],
        ),
        team_compounds=[],
        driver_strategies=[],
        data_quality='no_data',
    )
