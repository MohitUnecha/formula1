#!/usr/bin/env python3
"""Quick script to generate all track SVGs from FastF1."""
import fastf1
import numpy as np
import json
import os

fastf1.Cache.enable_cache(os.path.join(os.path.dirname(__file__), '.fastf1-cache'))

CIRCUITS = [
    (2024, 'Bahrain', 'bahrain'),
    (2024, 'Saudi Arabia', 'jeddah'),
    (2024, 'Australia', 'australia'),
    (2024, 'Japan', 'suzuka'),
    (2024, 'China', 'shanghai'),
    (2024, 'Miami', 'miami'),
    (2024, 'Emilia Romagna', 'imola'),
    (2024, 'Monaco', 'monaco'),
    (2024, 'Canada', 'montreal'),
    (2024, 'Spain', 'barcelona'),
    (2024, 'Austria', 'austria'),
    (2024, 'Great Britain', 'silverstone'),
    (2024, 'Hungary', 'hungary'),
    (2024, 'Belgium', 'spa'),
    (2024, 'Netherlands', 'zandvoort'),
    (2024, 'Italy', 'monza'),
    (2024, 'Azerbaijan', 'baku'),
    (2024, 'Singapore', 'singapore'),
    (2024, 'United States', 'cota'),
    (2024, 'Mexico', 'mexico'),
    (2024, 'Brazil', 'interlagos'),
    (2024, 'Las Vegas', 'lasvegas'),
    (2024, 'Qatar', 'lusail'),
    (2024, 'Abu Dhabi', 'abudhabi'),
]

def process_circuit(year, gp_name, key, n_pts=120, width=1000, height=700, padding=60):
    print(f"Loading {gp_name}...")
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
    
    # Start/finish position
    sf = {'x': round(nx[0]), 'y': round(ny[0])}
    
    print(f"  -> {len(x_raw)} pts -> SVG ({len(svg_path)} chars), {len(corners)} corners")
    return {
        'path': svg_path,
        'corners': corners,
        'rotation': rotation,
        'startFinish': sf,
    }


def main():
    import sys
    
    if '--single' in sys.argv:
        idx = sys.argv.index('--single')
        gp = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else 'Monaco'
        key = gp.lower().replace(' ', '_')
        result = process_circuit(2024, gp, key)
        print(f"\nPath: {result['path'][:200]}...")
        print(f"Corners: {result['corners']}")
        print(f"Start: {result['startFinish']}")
        return
    
    results = {}
    failed = []
    for year, gp, key in CIRCUITS:
        try:
            results[key] = process_circuit(year, gp, key)
        except Exception as e:
            print(f"  FAILED: {e}")
            failed.append((key, str(e)))
    
    out = os.path.join(os.path.dirname(__file__), 'data', 'track_svgs.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDone: {len(results)} OK, {len(failed)} failed")
    if failed:
        for k, e in failed:
            print(f"  {k}: {e}")


if __name__ == '__main__':
    main()
