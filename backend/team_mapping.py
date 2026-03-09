"""
Accurate driver-team mappings per season.

The `drivers` table stores only one team per driver (the last ingested).
This module provides the CORRECT team for each driver per season,
so APIs can return accurate data regardless of ingestion order.

Also includes DRIVER_NAME_OVERRIDES for codes reused by different people
(e.g. MSC = Michael Schumacher 2000-2012, Mick Schumacher 2021-2022).
"""

# ─── Driver-code → (first_name, last_name) overrides by season ────────
# Only needed when the same 3-letter code was used by different drivers.
DRIVER_NAME_OVERRIDES: dict[tuple[int, str], tuple[str, str]] = {}

# MSC: Michael Schumacher 2000-2012, Mick Schumacher 2021-2022
for _yr in range(2000, 2013):
    DRIVER_NAME_OVERRIDES[(_yr, "MSC")] = ("Michael", "Schumacher")


def get_driver_name(driver_code: str, season: int) -> tuple[str, str] | None:
    """
    Return (first_name, last_name) override for a driver code in a given season,
    or None if the DB-stored name is correct.
    """
    return DRIVER_NAME_OVERRIDES.get((season, driver_code.upper()))


# ─── (team_name, team_color_hex) per driver per season ────────────────
SEASON_TEAMS: dict[int, dict[str, tuple[str, str]]] = {
    # ═══════════════════════════════════════════════════════════════
    # 2000 Season
    # ═══════════════════════════════════════════════════════════════
    2000: {
        "MSC": ("Ferrari", "#DC0000"),
        "BAR": ("Ferrari", "#DC0000"),
        "COU": ("McLaren", "#A2A2A2"),
        "SCH": ("Williams", "#003399"),
        "BUT": ("Williams", "#003399"),
        "FIS": ("Benetton", "#00AADD"),
        "WUR": ("Benetton", "#00AADD"),
        "TRU": ("Jordan", "#EBC400"),
        "VIL": ("BAR", "#CC0000"),
        "ZON": ("BAR", "#CC0000"),
        "HEI": ("Prost", "#0090D0"),
        "NAN": ("Minardi", "#191919"),
        "DLR": ("Arrows", "#FF6600"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2001 Season
    # ═══════════════════════════════════════════════════════════════
    2001: {
        "MSC": ("Ferrari", "#DC0000"),
        "BAR": ("Ferrari", "#DC0000"),
        "COU": ("McLaren", "#A2A2A2"),
        "SCH": ("Williams", "#003399"),
        "MON": ("Williams", "#003399"),
        "FIS": ("Benetton", "#00AADD"),
        "BUT": ("Benetton", "#00AADD"),
        "TRU": ("Jordan", "#EBC400"),
        "ZON": ("Jordan", "#EBC400"),
        "VIL": ("BAR", "#CC0000"),
        "HEI": ("Sauber", "#006EAB"),
        "RAI": ("Sauber", "#006EAB"),
        "ALO": ("Minardi", "#191919"),
        "NAN": ("Minardi", "#191919"),
        "DLR": ("Jaguar", "#006633"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2002 Season
    # ═══════════════════════════════════════════════════════════════
    2002: {
        "MSC": ("Ferrari", "#DC0000"),
        "BAR": ("Ferrari", "#DC0000"),
        "COU": ("McLaren", "#A2A2A2"),
        "RAI": ("McLaren", "#A2A2A2"),
        "SCH": ("Williams", "#003399"),
        "MON": ("Williams", "#003399"),
        "TRU": ("Renault", "#FFD800"),
        "BUT": ("Renault", "#FFD800"),
        "FIS": ("Jordan", "#EBC400"),
        "SAT": ("Jordan", "#EBC400"),
        "VIL": ("BAR", "#CC0000"),
        "HEI": ("Sauber", "#006EAB"),
        "MAS": ("Sauber", "#006EAB"),
        "WEB": ("Minardi", "#191919"),
        "NAN": ("Williams", "#003399"),
        "DAV": ("Minardi", "#191919"),
        "DLR": ("Jaguar", "#006633"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2003 Season
    # ═══════════════════════════════════════════════════════════════
    2003: {
        "MSC": ("Ferrari", "#DC0000"),
        "BAR": ("Ferrari", "#DC0000"),
        "COU": ("McLaren", "#A2A2A2"),
        "RAI": ("McLaren", "#A2A2A2"),
        "MON": ("Williams", "#003399"),
        "SCH": ("Williams", "#003399"),
        "ALO": ("Renault", "#FFD800"),
        "TRU": ("Renault", "#FFD800"),
        "BUT": ("BAR", "#CC0000"),
        "VIL": ("BAR", "#CC0000"),
        "SAT": ("BAR", "#CC0000"),
        "FIS": ("Jordan", "#EBC400"),
        "HEI": ("Sauber", "#006EAB"),
        "WEB": ("Jaguar", "#006633"),
        "PIZ": ("Jaguar", "#006633"),
        "NAN": ("Minardi", "#191919"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2004 Season
    # ═══════════════════════════════════════════════════════════════
    2004: {
        "MSC": ("Ferrari", "#DC0000"),
        "BAR": ("Ferrari", "#DC0000"),
        "COU": ("McLaren", "#A2A2A2"),
        "RAI": ("McLaren", "#A2A2A2"),
        "MON": ("Williams", "#003399"),
        "SCH": ("Williams", "#003399"),
        "PIZ": ("Williams", "#003399"),
        "NAN": ("Williams", "#003399"),
        "ALO": ("Renault", "#FFD800"),
        "TRU": ("Renault", "#FFD800"),
        "BUT": ("BAR", "#CC0000"),
        "SAT": ("BAR", "#CC0000"),
        "MAS": ("Sauber", "#006EAB"),
        "FIS": ("Sauber", "#006EAB"),
        "WEB": ("Jaguar", "#006633"),
        "KLI": ("Jaguar", "#006633"),
        "GLO": ("Jordan", "#EBC400"),
        "HEI": ("Jordan", "#EBC400"),
        "ZON": ("Toyota", "#CD1E25"),
        "VIL": ("Renault", "#FFD800"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2005 Season
    # ═══════════════════════════════════════════════════════════════
    2005: {
        "MSC": ("Ferrari", "#DC0000"),
        "BAR": ("Ferrari", "#DC0000"),
        "RAI": ("McLaren", "#A2A2A2"),
        "MON": ("McLaren", "#A2A2A2"),
        "DLR": ("McLaren", "#A2A2A2"),
        "HEI": ("Williams", "#003399"),
        "WEB": ("Williams", "#003399"),
        "PIZ": ("Williams", "#003399"),
        "WUR": ("Williams", "#003399"),
        "DAV": ("Williams", "#003399"),
        "ALO": ("Renault", "#FFD800"),
        "FIS": ("Renault", "#FFD800"),
        "BUT": ("BAR", "#CC0000"),
        "SAT": ("BAR", "#CC0000"),
        "COU": ("Red Bull Racing", "#001E3C"),
        "KLI": ("Red Bull Racing", "#001E3C"),
        "SCH": ("Toyota", "#CD1E25"),
        "TRU": ("Toyota", "#CD1E25"),
        "ZON": ("Toyota", "#CD1E25"),
        "MAS": ("Sauber", "#006EAB"),
        "VIL": ("Sauber", "#006EAB"),
        "KAR": ("Jordan", "#EBC400"),
        "TMO": ("Jordan", "#EBC400"),
        "ALB": ("Minardi", "#191919"),
        "FRI": ("Minardi", "#191919"),
        "DOO": ("Minardi", "#191919"),
        "LIU": ("Minardi", "#191919"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2006 Season
    # ═══════════════════════════════════════════════════════════════
    2006: {
        "MSC": ("Ferrari", "#DC0000"),
        "MAS": ("Ferrari", "#DC0000"),
        "RAI": ("McLaren", "#A2A2A2"),
        "MON": ("McLaren", "#A2A2A2"),
        "DLR": ("McLaren", "#A2A2A2"),
        "ALO": ("Renault", "#FFD800"),
        "FIS": ("Renault", "#FFD800"),
        "BUT": ("Honda", "#006633"),
        "BAR": ("Honda", "#006633"),
        "ROS": ("Williams", "#003399"),
        "WEB": ("Williams", "#003399"),
        "SCH": ("Toyota", "#CD1E25"),
        "TRU": ("Toyota", "#CD1E25"),
        "COU": ("Red Bull Racing", "#001E3C"),
        "KLI": ("Red Bull Racing", "#001E3C"),
        "HEI": ("BMW Sauber", "#006EAB"),
        "VIL": ("BMW Sauber", "#006EAB"),
        "KUB": ("BMW Sauber", "#006EAB"),
        "LIU": ("Toro Rosso", "#001E3C"),
        "SPE": ("Toro Rosso", "#001E3C"),
        "ALB": ("Midland", "#FF6600"),
        "TMO": ("Midland", "#FF6600"),
        "SAT": ("Super Aguri", "#CC0000"),
        "IDE": ("Super Aguri", "#CC0000"),
        "FMO": ("Super Aguri", "#CC0000"),
        "YAM": ("Super Aguri", "#CC0000"),
        "DOO": ("Super Aguri", "#CC0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2007 Season
    # ═══════════════════════════════════════════════════════════════
    2007: {
        "RAI": ("Ferrari", "#DC0000"),
        "MAS": ("Ferrari", "#DC0000"),
        "ALO": ("McLaren", "#A2A2A2"),
        "HAM": ("McLaren", "#A2A2A2"),
        "HEI": ("BMW Sauber", "#006EAB"),
        "KUB": ("BMW Sauber", "#006EAB"),
        "FIS": ("Renault", "#FFD800"),
        "KOV": ("Renault", "#FFD800"),
        "ROS": ("Williams", "#003399"),
        "WUR": ("Williams", "#003399"),
        "NAK": ("Williams", "#003399"),
        "SCH": ("Toyota", "#CD1E25"),
        "TRU": ("Toyota", "#CD1E25"),
        "COU": ("Red Bull Racing", "#001E3C"),
        "WEB": ("Red Bull Racing", "#001E3C"),
        "VET": ("Toro Rosso", "#001E3C"),
        "LIU": ("Toro Rosso", "#001E3C"),
        "SPE": ("Toro Rosso", "#001E3C"),
        "BUT": ("Honda", "#006633"),
        "BAR": ("Honda", "#006633"),
        "SAT": ("Super Aguri", "#CC0000"),
        "DAV": ("Super Aguri", "#CC0000"),
        "SUT": ("Spyker", "#FF6600"),
        "ALB": ("Spyker", "#FF6600"),
        "WIN": ("Spyker", "#FF6600"),
        "YAM": ("Spyker", "#FF6600"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2008 Season
    # ═══════════════════════════════════════════════════════════════
    2008: {
        "RAI": ("Ferrari", "#DC0000"),
        "MAS": ("Ferrari", "#DC0000"),
        "HAM": ("McLaren", "#A2A2A2"),
        "KOV": ("McLaren", "#A2A2A2"),
        "HEI": ("BMW Sauber", "#006EAB"),
        "KUB": ("BMW Sauber", "#006EAB"),
        "ALO": ("Renault", "#FFD800"),
        "PIQ": ("Renault", "#FFD800"),
        "ROS": ("Williams", "#003399"),
        "NAK": ("Williams", "#003399"),
        "TRU": ("Toyota", "#CD1E25"),
        "GLO": ("Toyota", "#CD1E25"),
        "COU": ("Red Bull Racing", "#001E3C"),
        "WEB": ("Red Bull Racing", "#001E3C"),
        "VET": ("Toro Rosso", "#001E3C"),
        "BOU": ("Toro Rosso", "#001E3C"),
        "BUT": ("Honda", "#006633"),
        "BAR": ("Honda", "#006633"),
        "FIS": ("Force India", "#F596C8"),
        "SUT": ("Force India", "#F596C8"),
        "SAT": ("Super Aguri", "#CC0000"),
        "DAV": ("Super Aguri", "#CC0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2009 Season
    # ═══════════════════════════════════════════════════════════════
    2009: {
        "BUT": ("Brawn GP", "#D0F000"),
        "BAR": ("Brawn GP", "#D0F000"),
        "RAI": ("Ferrari", "#DC0000"),
        "MAS": ("Ferrari", "#DC0000"),
        "BAD": ("Ferrari", "#DC0000"),
        "FIS": ("Ferrari", "#DC0000"),
        "HAM": ("McLaren", "#A2A2A2"),
        "KOV": ("McLaren", "#A2A2A2"),
        "VET": ("Red Bull Racing", "#001E3C"),
        "WEB": ("Red Bull Racing", "#001E3C"),
        "ALO": ("Renault", "#FFD800"),
        "PIQ": ("Renault", "#FFD800"),
        "GRO": ("Renault", "#FFD800"),
        "ROS": ("Williams", "#003399"),
        "NAK": ("Williams", "#003399"),
        "TRU": ("Toyota", "#CD1E25"),
        "GLO": ("Toyota", "#CD1E25"),
        "KOB": ("Toyota", "#CD1E25"),
        "HEI": ("BMW Sauber", "#006EAB"),
        "KUB": ("BMW Sauber", "#006EAB"),
        "BUE": ("Toro Rosso", "#001E3C"),
        "ALG": ("Toro Rosso", "#001E3C"),
        "BOU": ("Toro Rosso", "#001E3C"),
        "SUT": ("Force India", "#F596C8"),
        "LIU": ("Force India", "#F596C8"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2010 Season
    # ═══════════════════════════════════════════════════════════════
    2010: {
        "VET": ("Red Bull Racing", "#001E3C"),
        "WEB": ("Red Bull Racing", "#001E3C"),
        "ALO": ("Ferrari", "#DC0000"),
        "MAS": ("Ferrari", "#DC0000"),
        "HAM": ("McLaren", "#A2A2A2"),
        "BUT": ("McLaren", "#A2A2A2"),
        "MSC": ("Mercedes", "#00D2BE"),
        "ROS": ("Mercedes", "#00D2BE"),
        "KUB": ("Renault", "#FFD800"),
        "PET": ("Renault", "#FFD800"),
        "BAR": ("Williams", "#003399"),
        "HUL": ("Williams", "#003399"),
        "SUT": ("Force India", "#F596C8"),
        "LIU": ("Force India", "#F596C8"),
        "BUE": ("Toro Rosso", "#001E3C"),
        "ALG": ("Toro Rosso", "#001E3C"),
        "KOB": ("Sauber", "#006EAB"),
        "DLR": ("Sauber", "#006EAB"),
        "HEI": ("Sauber", "#006EAB"),
        "TRU": ("Lotus", "#D5A027"),
        "KOV": ("Lotus", "#D5A027"),
        "SEN": ("HRT", "#6E0000"),
        "CHA": ("HRT", "#6E0000"),
        "KLI": ("HRT", "#6E0000"),
        "YAM": ("HRT", "#6E0000"),
        "GLO": ("Virgin", "#6E0000"),
        "DIG": ("Virgin", "#6E0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2011 Season
    # ═══════════════════════════════════════════════════════════════
    2011: {
        "VET": ("Red Bull Racing", "#001E3C"),
        "WEB": ("Red Bull Racing", "#001E3C"),
        "HAM": ("McLaren", "#A2A2A2"),
        "BUT": ("McLaren", "#A2A2A2"),
        "ALO": ("Ferrari", "#DC0000"),
        "MAS": ("Ferrari", "#DC0000"),
        "MSC": ("Mercedes", "#00D2BE"),
        "ROS": ("Mercedes", "#00D2BE"),
        "HEI": ("Renault", "#FFD800"),
        "PET": ("Renault", "#FFD800"),
        "SEN": ("Renault", "#FFD800"),
        "BAR": ("Williams", "#003399"),
        "MAL": ("Williams", "#003399"),
        "SUT": ("Force India", "#F596C8"),
        "DLR": ("Force India", "#F596C8"),
        "LIU": ("Force India", "#F596C8"),
        "BUE": ("Toro Rosso", "#001E3C"),
        "ALG": ("Toro Rosso", "#001E3C"),
        "RIC": ("Toro Rosso", "#001E3C"),
        "KOB": ("Sauber", "#006EAB"),
        "PER": ("Sauber", "#006EAB"),
        "TRU": ("Lotus", "#D5A027"),
        "KOV": ("Lotus", "#D5A027"),
        "GLO": ("Marussia", "#6E0000"),
        "DAM": ("Marussia", "#6E0000"),
        "KAR": ("HRT", "#6E0000"),
        "DIR": ("HRT", "#6E0000"),
        "CHA": ("HRT", "#6E0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2012 Season
    # ═══════════════════════════════════════════════════════════════
    2012: {
        "VET": ("Red Bull Racing", "#001E3C"),
        "WEB": ("Red Bull Racing", "#001E3C"),
        "HAM": ("McLaren", "#A2A2A2"),
        "BUT": ("McLaren", "#A2A2A2"),
        "ALO": ("Ferrari", "#DC0000"),
        "MAS": ("Ferrari", "#DC0000"),
        "MSC": ("Mercedes", "#00D2BE"),
        "ROS": ("Mercedes", "#00D2BE"),
        "RAI": ("Lotus", "#D5A027"),
        "GRO": ("Lotus", "#D5A027"),
        "MAL": ("Williams", "#003399"),
        "SEN": ("Williams", "#003399"),
        "HUL": ("Force India", "#F596C8"),
        "DIR": ("Force India", "#F596C8"),
        "VER": ("Toro Rosso", "#001E3C"),
        "RIC": ("Toro Rosso", "#001E3C"),
        "KOB": ("Sauber", "#006EAB"),
        "PER": ("Sauber", "#006EAB"),
        "PET": ("Caterham", "#006633"),
        "KOV": ("Caterham", "#006633"),
        "GLO": ("Marussia", "#6E0000"),
        "PIC": ("Marussia", "#6E0000"),
        "DLR": ("HRT", "#6E0000"),
        "KAR": ("HRT", "#6E0000"),
        "DAM": ("Marussia", "#6E0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2013 Season
    # ═══════════════════════════════════════════════════════════════
    2013: {
        "VET": ("Red Bull Racing", "#001E3C"),
        "WEB": ("Red Bull Racing", "#001E3C"),
        "ALO": ("Ferrari", "#DC0000"),
        "MAS": ("Ferrari", "#DC0000"),
        "BUT": ("McLaren", "#A2A2A2"),
        "PER": ("McLaren", "#A2A2A2"),
        "HAM": ("Mercedes", "#00D2BE"),
        "ROS": ("Mercedes", "#00D2BE"),
        "RAI": ("Lotus", "#D5A027"),
        "GRO": ("Lotus", "#D5A027"),
        "SUT": ("Force India", "#F596C8"),
        "DIR": ("Force India", "#F596C8"),
        "MAL": ("Williams", "#003399"),
        "BOT": ("Williams", "#003399"),
        "VER": ("Toro Rosso", "#001E3C"),
        "RIC": ("Toro Rosso", "#001E3C"),
        "HUL": ("Sauber", "#006EAB"),
        "GUT": ("Sauber", "#006EAB"),
        "PIC": ("Caterham", "#006633"),
        "VDG": ("Caterham", "#006633"),
        "KOV": ("Caterham", "#006633"),
        "BIA": ("Marussia", "#6E0000"),
        "CHI": ("Marussia", "#6E0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2014 Season
    # ═══════════════════════════════════════════════════════════════
    2014: {
        "HAM": ("Mercedes", "#00D2BE"),
        "ROS": ("Mercedes", "#00D2BE"),
        "VET": ("Red Bull Racing", "#001E3C"),
        "RIC": ("Red Bull Racing", "#001E3C"),
        "ALO": ("Ferrari", "#DC0000"),
        "RAI": ("Ferrari", "#DC0000"),
        "BUT": ("McLaren", "#A2A2A2"),
        "MAG": ("McLaren", "#A2A2A2"),
        "MAS": ("Williams", "#003399"),
        "BOT": ("Williams", "#003399"),
        "HUL": ("Force India", "#F596C8"),
        "PER": ("Force India", "#F596C8"),
        "VER": ("Toro Rosso", "#001E3C"),
        "KVY": ("Toro Rosso", "#001E3C"),
        "GRO": ("Lotus", "#D5A027"),
        "MAL": ("Lotus", "#D5A027"),
        "SUT": ("Sauber", "#006EAB"),
        "GUT": ("Sauber", "#006EAB"),
        "ERI": ("Caterham", "#006633"),
        "KOB": ("Caterham", "#006633"),
        "LOT": ("Caterham", "#006633"),
        "STE": ("Caterham", "#006633"),
        "BIA": ("Marussia", "#6E0000"),
        "CHI": ("Marussia", "#6E0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2015 Season
    # ═══════════════════════════════════════════════════════════════
    2015: {
        "HAM": ("Mercedes", "#00D2BE"),
        "ROS": ("Mercedes", "#00D2BE"),
        "VET": ("Ferrari", "#DC0000"),
        "RAI": ("Ferrari", "#DC0000"),
        "MAS": ("Williams", "#003399"),
        "BOT": ("Williams", "#003399"),
        "RIC": ("Red Bull Racing", "#001E3C"),
        "KVY": ("Red Bull Racing", "#001E3C"),
        "ALO": ("McLaren", "#A2A2A2"),
        "BUT": ("McLaren", "#A2A2A2"),
        "MAG": ("McLaren", "#A2A2A2"),
        "HUL": ("Force India", "#F596C8"),
        "PER": ("Force India", "#F596C8"),
        "VER": ("Toro Rosso", "#001E3C"),
        "SAI": ("Toro Rosso", "#001E3C"),
        "GRO": ("Lotus", "#D5A027"),
        "MAL": ("Lotus", "#D5A027"),
        "ERI": ("Sauber", "#006EAB"),
        "NAS": ("Sauber", "#006EAB"),
        "STE": ("Manor", "#6E0000"),
        "MER": ("Manor", "#6E0000"),
        "RSS": ("Manor", "#6E0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2016 Season
    # ═══════════════════════════════════════════════════════════════
    2016: {
        "HAM": ("Mercedes", "#00D2BE"),
        "ROS": ("Mercedes", "#00D2BE"),
        "VET": ("Ferrari", "#DC0000"),
        "RAI": ("Ferrari", "#DC0000"),
        "RIC": ("Red Bull Racing", "#001E3C"),
        "VER": ("Red Bull Racing", "#001E3C"),
        "KVY": ("Red Bull Racing", "#001E3C"),
        "MAS": ("Williams", "#003399"),
        "BOT": ("Williams", "#003399"),
        "ALO": ("McLaren", "#A2A2A2"),
        "BUT": ("McLaren", "#A2A2A2"),
        "VAN": ("McLaren", "#A2A2A2"),
        "PER": ("Force India", "#F596C8"),
        "HUL": ("Force India", "#F596C8"),
        "OCO": ("Force India", "#F596C8"),
        "SAI": ("Toro Rosso", "#001E3C"),
        "KVY": ("Toro Rosso", "#001E3C"),
        "MAG": ("Renault", "#FFD800"),
        "PAL": ("Renault", "#FFD800"),
        "GRO": ("Haas F1 Team", "#B6BABD"),
        "GUT": ("Haas F1 Team", "#B6BABD"),
        "ERI": ("Sauber", "#006EAB"),
        "NAS": ("Sauber", "#006EAB"),
        "WEH": ("Manor", "#6E0000"),
        "HAR": ("Manor", "#6E0000"),
        "OCO": ("Manor", "#6E0000"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2017 Season
    # ═══════════════════════════════════════════════════════════════
    2017: {
        "HAM": ("Mercedes", "#6CD3BF"),
        "BOT": ("Mercedes", "#6CD3BF"),
        "VET": ("Ferrari", "#DC0000"),
        "RAI": ("Ferrari", "#DC0000"),
        "RIC": ("Red Bull Racing", "#001E3C"),
        "VER": ("Red Bull Racing", "#001E3C"),
        "MAS": ("Williams", "#003399"),
        "STR": ("Williams", "#003399"),
        "DIR": ("Williams", "#003399"),
        "ALO": ("McLaren", "#FF8000"),
        "VAN": ("McLaren", "#FF8000"),
        "BUT": ("McLaren", "#FF8000"),
        "PER": ("Force India", "#F596C8"),
        "OCO": ("Force India", "#F596C8"),
        "SAI": ("Toro Rosso", "#001E3C"),
        "KVY": ("Toro Rosso", "#001E3C"),
        "GAS": ("Toro Rosso", "#001E3C"),
        "HUL": ("Renault", "#FFD800"),
        "PAL": ("Renault", "#FFD800"),
        "SAI": ("Renault", "#FFD800"),
        "GRO": ("Haas F1 Team", "#B6BABD"),
        "MAG": ("Haas F1 Team", "#B6BABD"),
        "ERI": ("Sauber", "#006EAB"),
        "WEH": ("Sauber", "#006EAB"),
        "GIO": ("Sauber", "#006EAB"),
        "HAR": ("Sauber", "#006EAB"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2025 Season
    # ═══════════════════════════════════════════════════════════════
    2025: {
        "VER": ("Red Bull Racing", "#3671C6"),
        "LAW": ("Red Bull Racing", "#3671C6"),
        "LEC": ("Ferrari", "#E8002D"),
        "HAM": ("Ferrari", "#E8002D"),
        "NOR": ("McLaren", "#FF8000"),
        "PIA": ("McLaren", "#FF8000"),
        "RUS": ("Mercedes", "#27F4D2"),
        "ANT": ("Mercedes", "#27F4D2"),
        "ALO": ("Aston Martin", "#229971"),
        "STR": ("Aston Martin", "#229971"),
        "GAS": ("Alpine", "#0093CC"),
        "DOO": ("Alpine", "#0093CC"),
        "COL": ("Alpine", "#0093CC"),  # replaced Doohan mid-season
        "ALB": ("Williams", "#64C4FF"),
        "SAI": ("Williams", "#64C4FF"),
        "OCO": ("Haas F1 Team", "#B6BABD"),
        "BEA": ("Haas F1 Team", "#B6BABD"),
        "TSU": ("Racing Bulls", "#6692FF"),
        "HAD": ("Racing Bulls", "#6692FF"),
        "HUL": ("Kick Sauber", "#52E252"),
        "BOR": ("Kick Sauber", "#52E252"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2024 Season
    # ═══════════════════════════════════════════════════════════════
    2024: {
        "VER": ("Red Bull Racing", "#3671C6"),
        "PER": ("Red Bull Racing", "#3671C6"),
        "LEC": ("Ferrari", "#E8002D"),
        "SAI": ("Ferrari", "#E8002D"),
        "BEA": ("Ferrari", "#E8002D"),  # sub at Saudi
        "NOR": ("McLaren", "#FF8000"),
        "PIA": ("McLaren", "#FF8000"),
        "HAM": ("Mercedes", "#27F4D2"),
        "RUS": ("Mercedes", "#27F4D2"),
        "ALO": ("Aston Martin", "#229971"),
        "STR": ("Aston Martin", "#229971"),
        "GAS": ("Alpine", "#0093CC"),
        "OCO": ("Alpine", "#0093CC"),
        "ALB": ("Williams", "#64C4FF"),
        "SAR": ("Williams", "#64C4FF"),
        "COL": ("Williams", "#64C4FF"),  # replaced Sargeant
        "MAG": ("Haas F1 Team", "#B6BABD"),
        "HUL": ("Haas F1 Team", "#B6BABD"),
        "RIC": ("RB", "#6692FF"),
        "TSU": ("RB", "#6692FF"),
        "LAW": ("RB", "#6692FF"),  # replaced Ricciardo
        "BOT": ("Kick Sauber", "#52E252"),
        "ZHO": ("Kick Sauber", "#52E252"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2023 Season
    # ═══════════════════════════════════════════════════════════════
    2023: {
        "VER": ("Red Bull Racing", "#3671C6"),
        "PER": ("Red Bull Racing", "#3671C6"),
        "LEC": ("Ferrari", "#E8002D"),
        "SAI": ("Ferrari", "#E8002D"),
        "NOR": ("McLaren", "#FF8000"),
        "PIA": ("McLaren", "#FF8000"),
        "HAM": ("Mercedes", "#27F4D2"),
        "RUS": ("Mercedes", "#27F4D2"),
        "ALO": ("Aston Martin", "#229971"),
        "STR": ("Aston Martin", "#229971"),
        "GAS": ("Alpine", "#0093CC"),
        "OCO": ("Alpine", "#0093CC"),
        "ALB": ("Williams", "#64C4FF"),
        "SAR": ("Williams", "#64C4FF"),
        "MAG": ("Haas F1 Team", "#B6BABD"),
        "HUL": ("Haas F1 Team", "#B6BABD"),
        "RIC": ("AlphaTauri", "#6692FF"),
        "TSU": ("AlphaTauri", "#6692FF"),
        "DEV": ("AlphaTauri", "#6692FF"),
        "LAW": ("AlphaTauri", "#6692FF"),
        "BOT": ("Alfa Romeo", "#C92D4B"),
        "ZHO": ("Alfa Romeo", "#C92D4B"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2022 Season
    # ═══════════════════════════════════════════════════════════════
    2022: {
        "VER": ("Red Bull Racing", "#3671C6"),
        "PER": ("Red Bull Racing", "#3671C6"),
        "LEC": ("Ferrari", "#E8002D"),
        "SAI": ("Ferrari", "#E8002D"),
        "NOR": ("McLaren", "#FF8000"),
        "RIC": ("McLaren", "#FF8000"),
        "HAM": ("Mercedes", "#27F4D2"),
        "RUS": ("Mercedes", "#27F4D2"),
        "ALO": ("Alpine", "#0093CC"),
        "OCO": ("Alpine", "#0093CC"),
        "ALB": ("Williams", "#64C4FF"),
        "LAT": ("Williams", "#64C4FF"),
        "DEV": ("Williams", "#64C4FF"),  # FP1 appearances
        "MAG": ("Haas F1 Team", "#B6BABD"),
        "MSC": ("Haas F1 Team", "#B6BABD"),
        "GAS": ("AlphaTauri", "#6692FF"),
        "TSU": ("AlphaTauri", "#6692FF"),
        "VET": ("Aston Martin", "#229971"),
        "STR": ("Aston Martin", "#229971"),
        "HUL": ("Aston Martin", "#229971"),  # sub for Vettel
        "BOT": ("Alfa Romeo", "#C92D4B"),
        "ZHO": ("Alfa Romeo", "#C92D4B"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2021 Season
    # ═══════════════════════════════════════════════════════════════
    2021: {
        "VER": ("Red Bull Racing", "#3671C6"),
        "PER": ("Red Bull Racing", "#3671C6"),
        "HAM": ("Mercedes", "#6CD3BF"),
        "BOT": ("Mercedes", "#6CD3BF"),
        "RUS": ("Mercedes", "#6CD3BF"),  # sub at Sakhir - actually 2020, but keep for safety
        "LEC": ("Ferrari", "#ED1C24"),
        "SAI": ("Ferrari", "#ED1C24"),
        "NOR": ("McLaren", "#FF8000"),
        "RIC": ("McLaren", "#FF8000"),
        "ALO": ("Alpine", "#0093CC"),
        "OCO": ("Alpine", "#0093CC"),
        "GAS": ("AlphaTauri", "#6692FF"),
        "TSU": ("AlphaTauri", "#6692FF"),
        "VET": ("Aston Martin", "#229971"),
        "STR": ("Aston Martin", "#229971"),
        "HUL": ("Aston Martin", "#229971"),
        "RAI": ("Alfa Romeo", "#C92D4B"),
        "GIO": ("Alfa Romeo", "#C92D4B"),
        "KUB": ("Alfa Romeo", "#C92D4B"),
        "LAT": ("Williams", "#64C4FF"),
        "RUS": ("Williams", "#64C4FF"),
        "MAZ": ("Haas F1 Team", "#B6BABD"),
        "MSC": ("Haas F1 Team", "#B6BABD"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2020 Season
    # ═══════════════════════════════════════════════════════════════
    2020: {
        "HAM": ("Mercedes", "#6CD3BF"),
        "BOT": ("Mercedes", "#6CD3BF"),
        "RUS": ("Williams", "#64C4FF"),
        "VER": ("Red Bull Racing", "#3671C6"),
        "ALB": ("Red Bull Racing", "#3671C6"),
        "LEC": ("Ferrari", "#ED1C24"),
        "VET": ("Ferrari", "#ED1C24"),
        "NOR": ("McLaren", "#FF8000"),
        "SAI": ("McLaren", "#FF8000"),
        "RIC": ("Renault", "#FFD800"),
        "OCO": ("Renault", "#FFD800"),
        "GAS": ("AlphaTauri", "#6692FF"),
        "KVY": ("AlphaTauri", "#6692FF"),
        "PER": ("Racing Point", "#F596C8"),
        "STR": ("Racing Point", "#F596C8"),
        "HUL": ("Racing Point", "#F596C8"),
        "RAI": ("Alfa Romeo", "#C92D4B"),
        "GIO": ("Alfa Romeo", "#C92D4B"),
        "KUB": ("Alfa Romeo", "#C92D4B"),
        "LAT": ("Williams", "#64C4FF"),
        "GRO": ("Haas F1 Team", "#B6BABD"),
        "MAG": ("Haas F1 Team", "#B6BABD"),
        "FIT": ("Haas F1 Team", "#B6BABD"),
        "AIT": ("Williams", "#64C4FF"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2019 Season
    # ═══════════════════════════════════════════════════════════════
    2019: {
        "HAM": ("Mercedes", "#6CD3BF"),
        "BOT": ("Mercedes", "#6CD3BF"),
        "VER": ("Red Bull Racing", "#3671C6"),
        "GAS": ("Red Bull Racing", "#3671C6"),
        "ALB": ("Red Bull Racing", "#3671C6"),
        "LEC": ("Ferrari", "#ED1C24"),
        "VET": ("Ferrari", "#ED1C24"),
        "NOR": ("McLaren", "#FF8000"),
        "SAI": ("McLaren", "#FF8000"),
        "RIC": ("Renault", "#FFD800"),
        "HUL": ("Renault", "#FFD800"),
        "KVY": ("Toro Rosso", "#6692FF"),
        "GAS": ("Toro Rosso", "#6692FF"),  # after demotion
        "ALB": ("Toro Rosso", "#6692FF"),  # before promotion
        "PER": ("Racing Point", "#F596C8"),
        "STR": ("Racing Point", "#F596C8"),
        "RAI": ("Alfa Romeo", "#C92D4B"),
        "GIO": ("Alfa Romeo", "#C92D4B"),
        "RUS": ("Williams", "#64C4FF"),
        "KUB": ("Williams", "#64C4FF"),
        "GRO": ("Haas F1 Team", "#B6BABD"),
        "MAG": ("Haas F1 Team", "#B6BABD"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2018 Season
    # ═══════════════════════════════════════════════════════════════
    2018: {
        "HAM": ("Mercedes", "#6CD3BF"),
        "BOT": ("Mercedes", "#6CD3BF"),
        "VER": ("Red Bull Racing", "#3671C6"),
        "RIC": ("Red Bull Racing", "#3671C6"),
        "VET": ("Ferrari", "#ED1C24"),
        "RAI": ("Ferrari", "#ED1C24"),
        "ALO": ("McLaren", "#FF8000"),
        "VAN": ("McLaren", "#FF8000"),
        "NOR": ("McLaren", "#FF8000"),
        "SAI": ("Renault", "#FFD800"),
        "HUL": ("Renault", "#FFD800"),
        "GAS": ("Toro Rosso", "#6692FF"),
        "HAR": ("Toro Rosso", "#6692FF"),
        "PER": ("Force India", "#F596C8"),
        "OCO": ("Force India", "#F596C8"),
        "STR": ("Williams", "#64C4FF"),
        "SIR": ("Williams", "#64C4FF"),
        "KUB": ("Williams", "#64C4FF"),
        "LEC": ("Sauber", "#C92D4B"),
        "ERI": ("Sauber", "#C92D4B"),
        "GRO": ("Haas F1 Team", "#B6BABD"),
        "MAG": ("Haas F1 Team", "#B6BABD"),
    },
    # ═══════════════════════════════════════════════════════════════
    # 2026 Season (projected)
    # ═══════════════════════════════════════════════════════════════
    2026: {
        "VER": ("Red Bull Racing", "#3671C6"),
        "LAW": ("Red Bull Racing", "#3671C6"),
        "LEC": ("Ferrari", "#E8002D"),
        "HAM": ("Ferrari", "#E8002D"),
        "NOR": ("McLaren", "#FF8000"),
        "PIA": ("McLaren", "#FF8000"),
        "RUS": ("Mercedes", "#27F4D2"),
        "ANT": ("Mercedes", "#27F4D2"),
        "ALO": ("Aston Martin", "#229971"),
        "STR": ("Aston Martin", "#229971"),
        "GAS": ("Alpine", "#0093CC"),
        "DOO": ("Alpine", "#0093CC"),
        "ALB": ("Williams", "#64C4FF"),
        "SAI": ("Williams", "#64C4FF"),
        "OCO": ("Haas F1 Team", "#B6BABD"),
        "BEA": ("Haas F1 Team", "#B6BABD"),
        "LIN": ("Racing Bulls", "#6692FF"),
        "HAD": ("Racing Bulls", "#6692FF"),
        "PER": ("Cadillac", "#C4A747"),
        "BOT": ("Cadillac", "#C4A747"),
        "HUL": ("Audi", "#990000"),
        "BOR": ("Audi", "#990000"),
    },
}


def get_team_for_driver(driver_code: str, season: int) -> tuple[str, str] | None:
    """
    Get the correct (team_name, team_color) for a driver in a given season.
    Returns None if not found in the mapping.
    """
    season_data = SEASON_TEAMS.get(season)
    if not season_data:
        return None
    return season_data.get(driver_code.upper())


def get_season_drivers(season: int) -> dict[str, tuple[str, str]]:
    """Get all driver-team mappings for a season."""
    return SEASON_TEAMS.get(season, {})
