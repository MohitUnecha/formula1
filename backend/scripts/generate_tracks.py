"""
Generate track coordinate data for all F1 circuits.
Run this script to pre-compute track data from FastF1.
Usage: python3 generate_tracks.py [--year 2024]
"""
import os
import sys
import json
import math
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from track_data import (
    save_track_data, get_track_data, list_available_tracks,
    _compute_edges, _build_svg_path, _ensure_dir, TRACK_DATA_DIR
)

# ─── Circuits to generate (year, round, circuit_key) ────
# Using 2024 season as the most recent with full data
CIRCUITS_2024 = [
    (2024, 1, "bahrain"),
    (2024, 2, "jeddah"),
    (2024, 3, "albert_park"),
    (2024, 4, "suzuka"),
    (2024, 5, "shanghai"),
    (2024, 6, "miami"),
    (2024, 7, "imola"),
    (2024, 8, "monaco"),
    (2024, 9, "montreal"),
    (2024, 10, "barcelona"),
    (2024, 11, "red_bull_ring"),
    (2024, 12, "silverstone"),
    (2024, 13, "hungaroring"),
    (2024, 14, "spa"),
    (2024, 15, "zandvoort"),
    (2024, 16, "monza"),
    (2024, 17, "baku"),
    (2024, 18, "singapore"),
    (2024, 19, "cota"),
    (2024, 20, "mexico_city"),
    (2024, 21, "interlagos"),
    (2024, 22, "las_vegas"),
    (2024, 23, "lusail"),
    (2024, 24, "yas_marina"),
]


def _make_circle_track(cx, cy, rx, ry, n=200, shape_fn=None):
    """Generate a track shape using parametric equations."""
    t = np.linspace(0, 2*math.pi, n, endpoint=False)
    if shape_fn:
        x, y = shape_fn(t)
    else:
        x = cx + rx * np.cos(t)
        y = cy + ry * np.sin(t)
    return [[round(float(xi), 1), round(float(yi), 1)] for xi, yi in zip(x, y)]


def generate_from_fastf1(year, round_num, circuit_key):
    """Try to generate from FastF1 live data."""
    try:
        from track_data import generate_track_from_fastf1
        print(f"  Fetching {circuit_key} from FastF1 ({year} R{round_num})...")
        data = generate_track_from_fastf1(year, round_num, "R")
        if data:
            save_track_data(circuit_key, data)
            print(f"  ✓ Saved {circuit_key}")
            return True
        else:
            print(f"  ✗ No data for {circuit_key}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def generate_all_from_fastf1():
    """Generate all track data from FastF1 (requires network, ~30 min total)."""
    import fastf1
    cache_dir = os.path.join(os.path.dirname(__file__), ".fastf1-cache")
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)
    
    for year, round_num, key in CIRCUITS_2024:
        if get_track_data(key):
            print(f"  Skipping {key} (already cached)")
            continue
        generate_from_fastf1(year, round_num, key)


def generate_single(year, round_num, circuit_key):
    """Generate a single track from FastF1."""
    import fastf1
    cache_dir = os.path.join(os.path.dirname(__file__), ".fastf1-cache")
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)
    return generate_from_fastf1(year, round_num, circuit_key)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate F1 track data")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--round", type=int, default=None)
    parser.add_argument("--circuit", type=str, default=None)
    parser.add_argument("--list", action="store_true", help="List available tracks")
    parser.add_argument("--all", action="store_true", help="Generate ALL tracks")
    
    args = parser.parse_args()
    
    if args.list:
        tracks = list_available_tracks()
        print(f"Available tracks ({len(tracks)}):")
        for t in tracks:
            print(f"  {t}")
    elif args.all:
        print(f"Generating all {len(CIRCUITS_2024)} tracks from FastF1...")
        generate_all_from_fastf1()
        print("Done!")
    elif args.round and args.circuit:
        generate_single(args.year, args.round, args.circuit)
    else:
        print("Use --all to generate all tracks, or --round N --circuit name for a single one")
        print("Use --list to show cached tracks")
