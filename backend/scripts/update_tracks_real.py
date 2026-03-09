#!/usr/bin/env python3
"""
Update tracks.ts with real FastF1 telemetry SVG paths.
Reads track_svgs.json (generated from FastF1 telemetry) and replaces
path, corners, and startFinish in the TypeScript file.
"""
import json
import re
import os

TRACKS_TS = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'lib', 'tracks.ts')
TRACK_DATA = os.path.join(os.path.dirname(__file__), 'data', 'track_svgs.json')


def main():
    with open(TRACK_DATA) as f:
        data = json.load(f)
    
    with open(TRACKS_TS) as f:
        content = f.read()
    
    updated = 0
    for key, track in data.items():
        svg_path = track['path']
        corners = track.get('corners', [])
        sf = track.get('startFinish', {})
        
        # Strategy: find the block for this track key and replace path, corners, startFinish
        # Pattern: key: { ... path: "...", ... corners: [...], ... startFinish: {x: N, y: N}, ...}
        
        # 1. Replace path string
        # Find:  key: {\n    ...\n    path: "...",
        # The path is on a line like:    path: "M ...",
        # We need to find it within the block starting with `key: {`
        
        # Find the block start
        block_pattern = rf'(\b{re.escape(key)}\s*:\s*\{{)'
        block_match = re.search(block_pattern, content)
        if not block_match:
            print(f"  WARNING: Could not find block for {key}")
            continue
        
        block_start = block_match.start()
        
        # Find the next track block or end of TRACKS object to delimit this block
        # Look for the closing of this block by counting braces
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
        
        # Replace path
        path_pattern = r'(path:\s*")[^"]*(")'
        new_path = f'\\1{svg_path}\\2'
        new_block = re.sub(path_pattern, new_path, block, count=1)
        
        # Replace corners array
        if corners:
            corners_ts = "[\n"
            for c in corners:
                corners_ts += f"      {{ x: {c['x']}, y: {c['y']}, number: {c['number']} }},\n"
            corners_ts += "    ]"
            
            # Match corners: [ ... ]
            corners_pattern = r'corners:\s*\[(?:[^\]]*\{[^}]*\}[^\]]*)*\]'
            corners_replacement = f'corners: {corners_ts}'
            new_block = re.sub(corners_pattern, corners_replacement, new_block, count=1, flags=re.DOTALL)
        
        # Replace startFinish
        if sf:
            sf_pattern = r'startFinish:\s*\{[^}]*\}'
            sf_replacement = f"startFinish: {{ x: {sf['x']}, y: {sf['y']} }}"
            new_block = re.sub(sf_pattern, sf_replacement, new_block, count=1)
        
        if new_block != block:
            content = content[:block_start] + new_block + content[block_end:]
            updated += 1
            print(f"  ✓ {key}: path={len(svg_path)} chars, {len(corners)} corners, sf=({sf.get('x','?')},{sf.get('y','?')})")
        else:
            print(f"  . {key}: no changes")
    
    with open(TRACKS_TS, 'w') as f:
        f.write(content)
    
    print(f"\n✓ Updated {updated}/24 tracks in {TRACKS_TS}")


if __name__ == '__main__':
    main()
