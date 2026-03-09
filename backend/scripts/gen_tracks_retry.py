#!/usr/bin/env python3
"""Retry failed tracks with 2023 data, then merge into track_svgs.json."""
import fastf1
import numpy as np
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
fastf1.Cache.enable_cache(os.path.join(os.path.dirname(__file__), 'data', 'fastf1_cache'))

FAILED_CIRCUITS = [
    (2023, 'Hungarian Grand Prix', 'hungary'),
    (2023, 'Belgian Grand Prix', 'spa'),
    (2023, 'Dutch Grand Prix', 'zandvoort'),
    (2023, 'Azerbaijan Grand Prix', 'baku'),
    (2023, 'Singapore Grand Prix', 'singapore'),
    (2023, 'Mexico City Grand Prix', 'mexico'),
    (2023, 'São Paulo Grand Prix', 'interlagos'),
    (2023, 'Las Vegas Grand Prix', 'lasvegas'),
    (2023, 'Qatar Grand Prix', 'lusail'),
    (2023, 'Abu Dhabi Grand Prix', 'abudhabi'),
]


def process_circuit(year, gp_name, key, n_pts=120, width=1000, height=700, padding=60):
    print(f"Loading {gp_name} ({year})...")
    session = fastf1.get_session(year, gp_name, 'R')
    session.load(telemetry=True, weather=False, messages=False)
    
    fastest = session.laps.pick_fastest()
    tel = fastest.get_telemetry()
    x_raw = tel['X'].values
    y_raw = tel['Y'].values
    
    # Get circuit info
    try:
        ci = session.get_circuit_info()
        rotation = float(ci.rotation)
        raw_corners = []
        for _, c in ci.corners.iterrows():
            raw_corners.append({
                'number': int(c['Number']),
                'x': float(c['X']),
                'y': float(c['Y']),
            })
    except Exception:
        rotation = 0
        raw_corners = []
    
    # Downsample
    indices = np.linspace(0, len(x_raw) - 1, n_pts, dtype=int)
    xd = x_raw[indices]
    yd = y_raw[indices]
    
    # Normalize
    xmin, xmax = xd.min(), xd.max()
    ymin, ymax = yd.min(), yd.max()
    data_w = xmax - xmin
    data_h = ymax - ymin
    
    if data_w == 0 or data_h == 0:
        raise ValueError("Degenerate data")
    
    scale = min((width - 2*padding) / data_w, (height - 2*padding) / data_h)
    sw = data_w * scale
    sh = data_h * scale
    ox = padding + (width - 2*padding - sw) / 2
    oy = padding + (height - 2*padding - sh) / 2
    
    nx = (xd - xmin) * scale + ox
    ny = (yd - ymin) * scale + oy
    
    # SVG path with cubic beziers
    parts = [f"M {nx[0]:.0f},{ny[0]:.0f}"]
    for i in range(1, len(nx) - 2, 3):
        if i + 2 < len(nx):
            parts.append(f"C {nx[i]:.0f},{ny[i]:.0f} {nx[i+1]:.0f},{ny[i+1]:.0f} {nx[i+2]:.0f},{ny[i+2]:.0f}")
    parts.append("Z")
    svg_path = " ".join(parts)
    
    # Transform corners
    corners = []
    for c in raw_corners:
        cx = (c['x'] - xmin) * scale + ox
        cy = (c['y'] - ymin) * scale + oy
        corners.append({'x': round(cx), 'y': round(cy), 'number': c['number']})
    
    sf = {'x': round(nx[0]), 'y': round(ny[0])}
    
    print(f"  -> {len(x_raw)} pts -> SVG ({len(svg_path)} chars), {len(corners)} corners")
    return {
        'path': svg_path,
        'corners': corners,
        'rotation': rotation,
        'startFinish': sf,
    }


def main():
    # Load existing
    out_path = os.path.join(os.path.dirname(__file__), 'data', 'track_svgs.json')
    existing = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            existing = json.load(f)
    
    print(f"Existing tracks: {len(existing)} ({list(existing.keys())})")
    
    for year, gp, key in FAILED_CIRCUITS:
        if key in existing:
            print(f"  {key}: already exists, skipping")
            continue
        try:
            existing[key] = process_circuit(year, gp, key)
        except Exception as e:
            print(f"  {key} FAILED: {e}")
    
    with open(out_path, 'w') as f:
        json.dump(existing, f, indent=2)
    
    print(f"\nTotal: {len(existing)} tracks")
    missing = [k for k in ['bahrain','jeddah','australia','suzuka','shanghai','miami','imola','monaco',
                           'montreal','barcelona','austria','silverstone','monza','cota','hungary',
                           'spa','zandvoort','baku','singapore','mexico','interlagos','lasvegas',
                           'lusail','abudhabi'] if k not in existing]
    if missing:
        print(f"Still missing: {missing}")
    else:
        print("All 24 tracks complete!")


if __name__ == '__main__':
    main()
