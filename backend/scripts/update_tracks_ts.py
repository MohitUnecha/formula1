#!/usr/bin/env python3
"""Update tracks.ts with accurate SVG paths."""
import json, re, os

# Load accurate track data
with open(os.path.join(os.path.dirname(__file__), 'data', 'accurate_tracks.json')) as f:
    tracks = json.load(f)

# Read current tracks.ts
ts_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'lib', 'tracks.ts')
with open(ts_path) as f:
    content = f.read()

# For each track, replace path, corners, and startFinish
for key, data in tracks.items():
    # Replace path
    path_pattern = rf'({key}:\s*\{{[^}}]*?path:\s*)"[^"]*"'
    new_path = data['path'].replace('\\', '\\\\')  # escape backslashes
    replacement = rf'\1"{new_path}"'
    content_new = re.sub(path_pattern, replacement, content, flags=re.DOTALL)
    if content_new != content:
        print(f"  Updated {key} path")
        content = content_new
    else:
        print(f"  WARNING: Could not find path for {key}")
    
    # Replace corners
    corners_str = json.dumps(data['corners'])
    # Convert JSON to TS format
    corners_str = corners_str.replace('"x":', '  x:').replace('"y":', 'y:').replace('"number":', 'number:').replace('"name":', 'name:')
    # Format nicely
    corners_lines = []
    for c in data['corners']:
        parts = [f"x: {c['x']}", f"y: {c['y']}", f"number: {c['number']}"]
        if 'name' in c:
            parts.append(f'name: "{c["name"]}"')
        corners_lines.append(f"      {{ {', '.join(parts)} }},")
    
    corners_block = "[\n" + "\n".join(corners_lines) + "\n    ]"
    
    # Find and replace corners array
    corner_pattern = rf'({key}:\s*\{{[^}}]*?corners:\s*)\[[^\]]*\]'
    content_new = re.sub(corner_pattern, rf'\1{corners_block}', content, flags=re.DOTALL)
    if content_new != content:
        print(f"  Updated {key} corners ({len(data['corners'])} corners)")
        content = content_new
    
    # Replace startFinish
    sf = data['startFinish']
    sf_pattern = rf'({key}:\s*\{{[^}}]*?startFinish:\s*)\{{[^}}]*\}}'
    content_new = re.sub(sf_pattern, rf'\1{{ x: {sf["x"]}, y: {sf["y"]} }}', content, flags=re.DOTALL)
    if content_new != content:
        print(f"  Updated {key} startFinish")
        content = content_new

with open(ts_path, 'w') as f:
    f.write(content)

print(f"\n✓ Updated {ts_path}")
