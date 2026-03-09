#!/bin/bash
cd /Users/mohitunecha/F1/backend
source venv/bin/activate
python3 -c "
import fastf1
import json, os, sys

fastf1.Cache.enable_cache('.fastf1-cache')

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

results = {}
for year, gp, key in CIRCUITS:
    try:
        print(f'Loading {gp}...', flush=True)
        s = fastf1.get_session(year, gp, 'R')
        s.load(telemetry=False, weather=False, messages=False, laps=False)
        ci = s.get_circuit_info()
        corners = []
        for _, c in ci.corners.iterrows():
            corners.append({'n': int(c['Number']), 'x': float(c['X']), 'y': float(c['Y'])})
        results[key] = {
            'rotation': float(ci.rotation),
            'corners': corners,
        }
        print(f'  OK: {len(corners)} corners, rot={ci.rotation}', flush=True)
    except Exception as e:
        print(f'  FAIL: {e}', flush=True)

os.makedirs('data', exist_ok=True)
with open('data/circuit_info.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f'Done: {len(results)} circuits saved')
"
