#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Frontend production build"
cd /Users/mohitunecha/F1/frontend
npm run build >/tmp/f1_front_build.log
echo "  OK: frontend build succeeded"

echo "[2/4] Backend import smoke"
cd /Users/mohitunecha/F1/backend
/Users/mohitunecha/F1/.venv/bin/python -c "import main; print('  OK: backend imports main app')"

echo "[3/4] Render blueprint present"
cd /Users/mohitunecha/F1
test -f render.yaml && echo "  OK: render.yaml found"

echo "[4/4] Deploy doc present"
test -f DEPLOY_RENDER.md && echo "  OK: DEPLOY_RENDER.md found"

echo "All predeploy checks passed."
