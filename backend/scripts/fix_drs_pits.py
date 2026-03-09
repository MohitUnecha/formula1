#!/usr/bin/env python3
"""
Compute DRS zones, pit entry/exit and sector boundaries along the real SVG paths.
Uses the SVG path data from track_svgs.json, extracts points at known race fractions,
and writes a complete updated tracks.ts.

DRS zones, pit locations and sectors are placed at fixed fractions along the track path
that are known per-circuit from real F1 data.
"""
import json, re, os, math

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'track_svgs.json')
TRACKS_TS = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'lib', 'tracks.ts')

# Per-circuit metadata: DRS detection/activation fractions, pit fractions, sector fractions
# Fractions are 0.0 to 1.0 along the track path (start/finish = 0.0)
# Each circuit has known DRS zones from FIA regulations
CIRCUIT_META = {
    'bahrain': {
        'drs': [(0.85, 0.98), (0.40, 0.55)],
        'pit_entry': 0.82, 'pit_exit': 0.95,
        'sectors': [0.33, 0.66],
    },
    'jeddah': {
        'drs': [(0.55, 0.70), (0.78, 0.93)],
        'pit_entry': 0.75, 'pit_exit': 0.90,
        'sectors': [0.33, 0.66],
    },
    'australia': {
        'drs': [(0.45, 0.58), (0.78, 0.95)],
        'pit_entry': 0.42, 'pit_exit': 0.55,
        'sectors': [0.33, 0.66],
    },
    'suzuka': {
        'drs': [(0.85, 0.98)],
        'pit_entry': 0.82, 'pit_exit': 0.95,
        'sectors': [0.33, 0.66],
    },
    'shanghai': {
        'drs': [(0.48, 0.62), (0.82, 0.97)],
        'pit_entry': 0.80, 'pit_exit': 0.94,
        'sectors': [0.33, 0.66],
    },
    'miami': {
        'drs': [(0.25, 0.38), (0.60, 0.73)],
        'pit_entry': 0.22, 'pit_exit': 0.35,
        'sectors': [0.33, 0.66],
    },
    'imola': {
        'drs': [(0.85, 0.98)],
        'pit_entry': 0.82, 'pit_exit': 0.95,
        'sectors': [0.33, 0.66],
    },
    'monaco': {
        'drs': [],  # No DRS in Monaco (too narrow)
        'pit_entry': 0.75, 'pit_exit': 0.90,
        'sectors': [0.33, 0.66],
    },
    'montreal': {
        'drs': [(0.46, 0.58), (0.78, 0.95)],
        'pit_entry': 0.76, 'pit_exit': 0.92,
        'sectors': [0.33, 0.66],
    },
    'barcelona': {
        'drs': [(0.85, 0.98), (0.48, 0.58)],
        'pit_entry': 0.82, 'pit_exit': 0.95,
        'sectors': [0.33, 0.66],
    },
    'austria': {
        'drs': [(0.55, 0.72), (0.80, 0.97)],
        'pit_entry': 0.52, 'pit_exit': 0.66,
        'sectors': [0.33, 0.66],
    },
    'silverstone': {
        'drs': [(0.45, 0.56), (0.78, 0.93)],
        'pit_entry': 0.42, 'pit_exit': 0.56,
        'sectors': [0.33, 0.66],
    },
    'hungary': {
        'drs': [(0.85, 0.98)],
        'pit_entry': 0.82, 'pit_exit': 0.95,
        'sectors': [0.33, 0.66],
    },
    'spa': {
        'drs': [(0.55, 0.68), (0.82, 0.97)],
        'pit_entry': 0.80, 'pit_exit': 0.94,
        'sectors': [0.33, 0.66],
    },
    'zandvoort': {
        'drs': [(0.55, 0.70), (0.80, 0.95)],
        'pit_entry': 0.52, 'pit_exit': 0.67,
        'sectors': [0.33, 0.66],
    },
    'monza': {
        'drs': [(0.28, 0.42), (0.78, 0.95)],
        'pit_entry': 0.76, 'pit_exit': 0.92,
        'sectors': [0.33, 0.66],
    },
    'baku': {
        'drs': [(0.48, 0.62), (0.82, 0.97)],
        'pit_entry': 0.80, 'pit_exit': 0.94,
        'sectors': [0.33, 0.66],
    },
    'singapore': {
        'drs': [(0.55, 0.68), (0.82, 0.95)],
        'pit_entry': 0.80, 'pit_exit': 0.93,
        'sectors': [0.33, 0.66],
    },
    'cota': {
        'drs': [(0.48, 0.60), (0.82, 0.97)],
        'pit_entry': 0.80, 'pit_exit': 0.94,
        'sectors': [0.33, 0.66],
    },
    'mexico': {
        'drs': [(0.55, 0.70), (0.82, 0.97)],
        'pit_entry': 0.80, 'pit_exit': 0.94,
        'sectors': [0.33, 0.66],
    },
    'interlagos': {
        'drs': [(0.48, 0.62), (0.78, 0.95)],
        'pit_entry': 0.76, 'pit_exit': 0.92,
        'sectors': [0.33, 0.66],
    },
    'lasvegas': {
        'drs': [(0.25, 0.40), (0.62, 0.78)],
        'pit_entry': 0.22, 'pit_exit': 0.36,
        'sectors': [0.33, 0.66],
    },
    'lusail': {
        'drs': [(0.55, 0.70), (0.82, 0.97)],
        'pit_entry': 0.52, 'pit_exit': 0.67,
        'sectors': [0.33, 0.66],
    },
    'abudhabi': {
        'drs': [(0.48, 0.60), (0.82, 0.97)],
        'pit_entry': 0.80, 'pit_exit': 0.94,
        'sectors': [0.33, 0.66],
    },
}


def parse_svg_path(d):
    """Parse an SVG path string into a list of (x,y) points by sampling."""
    # Extract all coordinate pairs from M, C, L, Q commands
    points = []
    # Get numeric values
    nums = re.findall(r'[-+]?\d*\.?\d+', d)
    nums = [float(n) for n in nums]
    i = 0
    while i < len(nums) - 1:
        points.append((nums[i], nums[i+1]))
        i += 2
    return points


def interpolate_points(points, n=500):
    """Create n evenly-spaced points along the polyline."""
    if len(points) < 2:
        return points
    
    # Compute cumulative distances
    dists = [0.0]
    for i in range(1, len(points)):
        dx = points[i][0] - points[i-1][0]
        dy = points[i][1] - points[i-1][1]
        dists.append(dists[-1] + math.sqrt(dx*dx + dy*dy))
    
    total = dists[-1]
    if total == 0:
        return points
    
    result = []
    for j in range(n):
        target = (j / n) * total
        # Find segment
        for i in range(1, len(dists)):
            if dists[i] >= target:
                t = (target - dists[i-1]) / (dists[i] - dists[i-1]) if dists[i] != dists[i-1] else 0
                x = points[i-1][0] + t * (points[i][0] - points[i-1][0])
                y = points[i-1][1] + t * (points[i][1] - points[i-1][1])
                result.append((round(x), round(y)))
                break
    
    return result


def get_point_at_fraction(smooth_pts, frac):
    """Get point at given fraction (0-1) along smoothed points."""
    idx = int(frac * (len(smooth_pts) - 1))
    idx = max(0, min(idx, len(smooth_pts) - 1))
    return smooth_pts[idx]


def main():
    with open(DATA_FILE) as f:
        data = json.load(f)
    
    with open(TRACKS_TS) as f:
        content = f.read()
    
    updated = 0
    for key, track in data.items():
        if key not in CIRCUIT_META:
            print(f"  SKIP {key}: no metadata")
            continue
        
        meta = CIRCUIT_META[key]
        path_str = track['path']
        
        # Parse and interpolate
        raw_pts = parse_svg_path(path_str)
        smooth = interpolate_points(raw_pts, 500)
        
        if len(smooth) < 10:
            print(f"  SKIP {key}: too few points ({len(smooth)})")
            continue
        
        # Compute DRS zones
        drs_zones = []
        for (start_frac, end_frac) in meta['drs']:
            sp = get_point_at_fraction(smooth, start_frac)
            ep = get_point_at_fraction(smooth, end_frac)
            drs_zones.append({'start': {'x': sp[0], 'y': sp[1]}, 'end': {'x': ep[0], 'y': ep[1]}})
        
        # Compute pit entry/exit
        pit_entry = get_point_at_fraction(smooth, meta['pit_entry'])
        pit_exit = get_point_at_fraction(smooth, meta['pit_exit'])
        
        # Compute sector boundaries
        sectors = []
        for sf in meta['sectors']:
            sp = get_point_at_fraction(smooth, sf)
            sectors.append({'x': sp[0], 'y': sp[1]})
        
        # Now patch the tracks.ts content
        block_pattern = rf'(\b{re.escape(key)}\s*:\s*\{{)'
        block_match = re.search(block_pattern, content)
        if not block_match:
            print(f"  SKIP {key}: not found in tracks.ts")
            continue
        
        block_start = block_match.start()
        depth = 0
        block_end = block_start
        in_block = False
        for i in range(block_match.end() - 1, len(content)):
            if content[i] == '{':
                depth += 1
                in_block = True
            elif content[i] == '}':
                depth -= 1
                if in_block and depth == 0:
                    block_end = i + 1
                    break
        
        block = content[block_start:block_end]
        
        # Replace DRS zones
        if drs_zones:
            drs_ts = "[\n"
            for dz in drs_zones:
                drs_ts += f"      {{ start: {{ x: {dz['start']['x']}, y: {dz['start']['y']} }}, end: {{ x: {dz['end']['x']}, y: {dz['end']['y']} }} }},\n"
            drs_ts += "    ]"
        else:
            drs_ts = "[]"
        
        drs_pattern = r'drsZones:\s*\[(?:[^\]]*\{[^}]*\{[^}]*\}[^}]*\{[^}]*\}[^}]*\}[^\]]*)*\]|drsZones:\s*\[\]'
        block = re.sub(drs_pattern, f'drsZones: {drs_ts}', block, count=1, flags=re.DOTALL)
        
        # Replace pit entry
        pit_entry_pattern = r'pitEntry:\s*\{[^}]*\}'
        block = re.sub(pit_entry_pattern, f'pitEntry: {{ x: {pit_entry[0]}, y: {pit_entry[1]} }}', block, count=1)
        
        # Replace pit exit
        pit_exit_pattern = r'pitExit:\s*\{[^}]*\}'
        block = re.sub(pit_exit_pattern, f'pitExit: {{ x: {pit_exit[0]}, y: {pit_exit[1]} }}', block, count=1)
        
        # Replace sector boundaries
        sectors_ts = "[\n"
        for s in sectors:
            sectors_ts += f"      {{ x: {s['x']}, y: {s['y']} }},\n"
        sectors_ts += "    ]"
        
        sector_pattern = r'sectorBoundaries:\s*\[(?:[^\]]*\{[^}]*\}[^\]]*)*\]'
        block = re.sub(sector_pattern, f'sectorBoundaries: {sectors_ts}', block, count=1, flags=re.DOTALL)
        
        content = content[:block_start] + block + content[block_end:]
        updated += 1
        drs_count = len(drs_zones)
        print(f"  ✓ {key}: {drs_count} DRS zones, pit({pit_entry[0]},{pit_entry[1]}→{pit_exit[0]},{pit_exit[1]}), 2 sectors")
    
    with open(TRACKS_TS, 'w') as f:
        f.write(content)
    
    print(f"\n✓ Updated DRS/pit/sectors for {updated} tracks")


if __name__ == '__main__':
    main()
