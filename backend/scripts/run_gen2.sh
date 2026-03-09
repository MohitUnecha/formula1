#!/bin/bash
cd /Users/mohitunecha/F1/backend
source venv/bin/activate
python3 gen_tracks_quick.py --single Monaco > /Users/mohitunecha/F1/backend/data/gen_log.txt 2>&1
echo "EXIT_CODE=$?" >> /Users/mohitunecha/F1/backend/data/gen_log.txt
