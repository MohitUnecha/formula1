#!/usr/bin/env python3
"""
Generate accurate SVG track paths from FastF1 telemetry data.
Uses the fastest lap X/Y telemetry to build track centerlines,
then converts them to normalized SVG paths (0-1000 range).
"""
import sys
import os
import json
import numpy as np

# Add parent directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fetch_track_coords(year, gp_name, session_type='R'):
    """Fetch track X/Y coordinates from FastF1."""
    import fastf1
    fastf1.Cache.enable_cache(os.path.join(os.path.dirname(__file__), '.fastf1-cache'))
    
    print(f"Loading {year} {gp_name} {session_type}...")
    session = fastf1.get_session(year, gp_name, session_type)
    session.load(telemetry=True, weather=False, messages=False)
    
    # Get fastest lap telemetry
    fastest = session.laps.pick_fastest()
    tel = fastest.get_telemetry()
    
    x = tel['X'].values
    y = tel['Y'].values
    
    # Get circuit info
    try:
        circuit_info = session.get_circuit_info()
        rotation = float(circuit_info.rotation)
        corners = []
        for _, corner in circuit_info.corners.iterrows():
            corners.append({
                'number': int(corner['Number']),
                'letter': str(corner.get('Letter', '')),
                'x': float(corner['X']),
                'y': float(corner['Y']),
                'angle': float(corner.get('Angle', 0)),
                'distance': float(corner.get('Distance', 0)),
            })
    except:
        rotation = 0
        corners = []
    
    return x, y, rotation, corners


def coords_to_svg_path(x, y, target_points=150, width=1000, height=700, padding=60):
    """Convert raw X/Y coordinates to a normalized SVG path string."""
    # Apply rotation if needed
    n = len(x)
    if n < 10:
        raise ValueError("Too few points")
    
    # Downsample to target_points using uniform spacing
    indices = np.linspace(0, n - 1, target_points, dtype=int)
    x_ds = x[indices]
    y_ds = y[indices]
    
    # Compute bounds
    x_min, x_max = x_ds.min(), x_ds.max()
    y_min, y_max = y_ds.min(), y_ds.max()
    
    # Scale to fit in width x height with padding
    data_w = x_max - x_min
    data_h = y_max - y_min
    
    if data_w == 0 or data_h == 0:
        raise ValueError("Degenerate track data")
    
    scale_x = (width - 2 * padding) / data_w
    scale_y = (height - 2 * padding) / data_h
    scale = min(scale_x, scale_y)
    
    # Center the track
    scaled_w = data_w * scale
    scaled_h = data_h * scale
    offset_x = padding + (width - 2 * padding - scaled_w) / 2
    offset_y = padding + (height - 2 * padding - scaled_h) / 2
    
    # Normalize coordinates
    nx = (x_ds - x_min) * scale + offset_x
    ny = (y_ds - y_min) * scale + offset_y
    
    # Build SVG path with smooth curves
    parts = [f"M {nx[0]:.0f},{ny[0]:.0f}"]
    
    # Use cubic bezier curves for smoothness
    for i in range(1, len(nx) - 2, 3):
        if i + 2 < len(nx):
            parts.append(f"C {nx[i]:.0f},{ny[i]:.0f} {nx[i+1]:.0f},{ny[i+1]:.0f} {nx[i+2]:.0f},{ny[i+2]:.0f}")
        elif i + 1 < len(nx):
            parts.append(f"Q {nx[i]:.0f},{ny[i]:.0f} {nx[i+1]:.0f},{ny[i+1]:.0f}")
        else:
            parts.append(f"L {nx[i]:.0f},{ny[i]:.0f}")
    
    parts.append("Z")
    
    return " ".join(parts), nx, ny, scale, offset_x, offset_y, x_min, y_min


def transform_corner(corner, scale, offset_x, offset_y, x_min, y_min):
    """Transform a corner from world coords to SVG coords."""
    sx = (corner['x'] - x_min) * scale + offset_x
    sy = (corner['y'] - y_min) * scale + offset_y
    return {'x': round(sx), 'y': round(sy), 'number': corner['number']}


def generate_all_tracks():
    """Generate SVG paths for all 2024 circuits."""
    circuits = [
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
    
    results = {}
    for year, gp, key in circuits:
        try:
            print(f"\n{'='*50}")
            print(f"Processing: {gp} ({key})")
            x, y, rotation, corners = fetch_track_coords(year, gp)
            
            svg_path, nx, ny, scale, ox, oy, xmin, ymin = coords_to_svg_path(x, y)
            
            # Transform corners
            svg_corners = []
            for c in corners:
                sc = transform_corner(c, scale, ox, oy, xmin, ymin)
                svg_corners.append(sc)
            
            results[key] = {
                'path': svg_path,
                'corners': svg_corners,
                'rotation': rotation,
                'start_finish': {'x': round(nx[0]), 'y': round(ny[0])},
            }
            print(f"  OK - {len(x)} points -> SVG path ({len(svg_path)} chars)")
            
        except Exception as e:
            print(f"  FAILED: {e}")
    
    # Save results
    out_path = os.path.join(os.path.dirname(__file__), 'data', 'track_svgs.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} tracks to {out_path}")
    
    return results


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--single':
        # Quick test with one circuit
        gp = sys.argv[2] if len(sys.argv) > 2 else 'Monaco'
        x, y, rot, corners = fetch_track_coords(2024, gp)
        svg, *_ = coords_to_svg_path(x, y)
        print(f"\nSVG Path ({len(svg)} chars):")
        print(svg[:500])
        print(f"\nRotation: {rot}")
        print(f"Corners: {len(corners)}")
    else:
        generate_all_tracks()
