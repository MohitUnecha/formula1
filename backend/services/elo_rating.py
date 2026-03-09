"""
F1 Elo Rating System — "The New Trick"

Chess-style Elo applied to F1: every driver starts at 1500 and gains/loses
points after each race based on their finishing position relative to every
other driver in the field.  The K-factor adapts: rookies move faster,
veterans are more stable, and recency matters.

This gives a single "true skill" number per driver that naturally handles:
  - Momentum (winning streak → rating climbs)
  - Car performance (winning in a slower car → bigger Elo gain)
  - Consistency (steady top-5 finishes → high stable rating)
  - Decline detection (string of bad results → rating drops)

The Elo difference between two drivers can directly predict head-to-head
probability via the logistic function, which is the "new trick" for the
prediction model.
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────
INITIAL_RATING = 1500.0
K_BASE = 32.0          # Base K-factor (how much a single race can swing)
K_ROOKIE_MULT = 1.5    # Rookies move faster (first 15 races)
K_VETERAN_MULT = 0.8   # Veterans are more stable (100+ races)
DECAY_RATE = 0.02      # Rating decays toward 1500 when driver misses races
ROOKIE_THRESHOLD = 15   # Races before considered non-rookie
VETERAN_THRESHOLD = 100 # Races before considered veteran


@dataclass
class DriverElo:
    """Tracks a single driver's Elo state."""
    code: str
    rating: float = INITIAL_RATING
    peak_rating: float = INITIAL_RATING
    races_completed: int = 0
    wins: int = 0
    last_season: int = 0
    history: List[Tuple[int, int, float]] = field(default_factory=list)  # (season, round, rating)

    @property
    def k_factor(self) -> float:
        """Adaptive K-factor based on experience."""
        if self.races_completed < ROOKIE_THRESHOLD:
            return K_BASE * K_ROOKIE_MULT
        elif self.races_completed >= VETERAN_THRESHOLD:
            return K_BASE * K_VETERAN_MULT
        return K_BASE

    @property
    def tier(self) -> str:
        if self.rating >= 1800:
            return "ELITE"
        elif self.rating >= 1650:
            return "TOP"
        elif self.rating >= 1500:
            return "STRONG"
        elif self.rating >= 1350:
            return "MID"
        else:
            return "DEVELOPING"


class F1EloSystem:
    """
    Computes and stores Elo ratings for all F1 drivers across seasons.

    Usage:
        elo = F1EloSystem()
        elo.build_from_db(db_session)
        rating = elo.get_rating("VER")  # → 1823.5
        prob = elo.head_to_head("VER", "HAM")  # → 0.68 (VER 68% to beat HAM)
    """

    def __init__(self):
        self.drivers: Dict[str, DriverElo] = {}
        self._built = False

    def _get_or_create(self, code: str) -> DriverElo:
        if code not in self.drivers:
            self.drivers[code] = DriverElo(code=code)
        return self.drivers[code]

    @staticmethod
    def expected_score(rating_a: float, rating_b: float) -> float:
        """Logistic expected score: probability that A beats B."""
        return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))

    def head_to_head(self, code_a: str, code_b: str) -> float:
        """Probability that driver A finishes ahead of driver B."""
        ra = self.get_rating(code_a)
        rb = self.get_rating(code_b)
        return self.expected_score(ra, rb)

    def get_rating(self, code: str) -> float:
        d = self.drivers.get(code)
        return d.rating if d else INITIAL_RATING

    def get_driver_elo(self, code: str) -> Optional[DriverElo]:
        return self.drivers.get(code)

    def get_rankings(self, top_n: int = 30) -> List[DriverElo]:
        """Get drivers sorted by current rating."""
        active = sorted(self.drivers.values(), key=lambda d: d.rating, reverse=True)
        return active[:top_n]

    def process_race(self, season: int, round_num: int,
                     results: List[Tuple[str, int, bool]]):
        """
        Update ratings after a race.

        Args:
            season: Season year
            round_num: Round number
            results: List of (driver_code, position, is_dnf)
        """
        finishers = [(code, pos) for code, pos, dnf in results if not dnf]
        dnf_drivers = [code for code, pos, dnf in results if dnf]

        n = len(finishers)
        if n < 2:
            return

        # Apply season-gap decay (if driver wasn't in last season)
        for code, pos in finishers:
            d = self._get_or_create(code)
            if d.last_season > 0 and season > d.last_season + 1:
                gap = season - d.last_season
                d.rating = INITIAL_RATING + (d.rating - INITIAL_RATING) * (1 - DECAY_RATE * gap * 5)

        # ── Elo update: compare each pair of finishers ──
        # For each pair (i, j) where i finished ahead of j:
        #   score_i = 1.0, score_j = 0.0
        # Then update both ratings
        rating_changes: Dict[str, float] = {code: 0.0 for code, _ in finishers}

        for i in range(n):
            for j in range(i + 1, n):
                code_i, pos_i = finishers[i]
                code_j, pos_j = finishers[j]
                di = self._get_or_create(code_i)
                dj = self._get_or_create(code_j)

                expected_i = self.expected_score(di.rating, dj.rating)
                actual_i = 1.0  # i finished ahead of j (sorted by position)

                # Scale K by number of comparisons so total change is reasonable
                k_scale = 2.0 / (n - 1)
                ki = di.k_factor * k_scale
                kj = dj.k_factor * k_scale

                # Bonus for large upsets (lower-rated beating higher-rated)
                upset = 1.0
                if di.rating < dj.rating and (pos_j - pos_i) > 3:
                    upset = 1.3

                rating_changes[code_i] += ki * (actual_i - expected_i) * upset
                rating_changes[code_j] += kj * (0.0 - (1.0 - expected_i)) * upset

        # ── Apply changes ──
        for code, delta in rating_changes.items():
            d = self._get_or_create(code)
            d.rating += delta
            d.rating = max(800, min(2400, d.rating))  # Clamp
            d.races_completed += 1
            d.last_season = season
            if d.rating > d.peak_rating:
                d.peak_rating = d.rating
            if code == finishers[0][0]:
                d.wins += 1
            d.history.append((season, round_num, round(d.rating, 1)))

        # DNF drivers get a small penalty
        for code in dnf_drivers:
            d = self._get_or_create(code)
            penalty = d.k_factor * 0.15  # ~5 point penalty
            d.rating = max(800, d.rating - penalty)
            d.races_completed += 1
            d.last_season = season
            d.history.append((season, round_num, round(d.rating, 1)))

    def build_from_db(self, db_session) -> int:
        """
        Build Elo ratings from the entire database history.

        Args:
            db_session: SQLAlchemy session

        Returns:
            Number of races processed
        """
        from models import Event, Session as DBSession, DriverSession, Driver

        # Get all race sessions ordered chronologically
        races = db_session.query(DBSession).join(Event).filter(
            DBSession.session_type == 'R'
        ).order_by(Event.season, Event.round).all()

        count = 0
        for session in races:
            event = session.event
            if not event:
                continue

            # Get results for this race
            driver_sessions = db_session.query(DriverSession).join(Driver).filter(
                DriverSession.session_id == session.session_id
            ).all()

            results = []
            for ds in driver_sessions:
                if not ds.driver:
                    continue
                code = ds.driver.driver_code
                pos = ds.position or 99
                is_dnf = ds.dnf or (ds.status and ds.status not in ('Finished', '') and not ds.status.startswith('+'))
                results.append((code, pos, is_dnf))

            # Sort by position (finishers first, then DNFs)
            results.sort(key=lambda x: (x[2], x[1]))  # DNFs at end

            if results:
                self.process_race(event.season, event.round, results)
                count += 1

        self._built = True
        logger.info(f"Elo system built from {count} races, {len(self.drivers)} drivers rated")
        return count

    def to_dict(self) -> Dict:
        """Serialize current state."""
        return {
            code: {
                "rating": round(d.rating, 1),
                "peak": round(d.peak_rating, 1),
                "races": d.races_completed,
                "wins": d.wins,
                "tier": d.tier,
                "last_5": [h[2] for h in d.history[-5:]] if d.history else [],
            }
            for code, d in sorted(self.drivers.items(), key=lambda x: x[1].rating, reverse=True)
        }


# ── Module-level singleton ────────────────────────────────────────────────
_elo_instance: Optional[F1EloSystem] = None


def get_elo_system(db_session=None) -> F1EloSystem:
    """Get or build the Elo rating system (lazy singleton)."""
    global _elo_instance
    if _elo_instance is None or not _elo_instance._built:
        if db_session is None:
            raise RuntimeError("DB session required to build Elo system")
        _elo_instance = F1EloSystem()
        _elo_instance.build_from_db(db_session)
    return _elo_instance


def reset_elo():
    """Force rebuild on next access."""
    global _elo_instance
    _elo_instance = None
