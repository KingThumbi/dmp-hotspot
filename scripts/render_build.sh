#!/usr/bin/env bash
set -euo pipefail

# Backend Render build step.
# Builds Python dependencies and the React admin bundle that Flask serves
# from frontend/dist for /admin-ui/* deep links.

echo "Installing backend Python dependencies..."
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
  PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif [ -x "./venv/bin/python" ]; then
  PYTHON_BIN="./venv/bin/python"
fi

"${PYTHON_BIN}" -m pip install -r requirements.txt

echo "Installing frontend dependencies..."
npm ci --prefix frontend

echo "Building React frontend..."
npm run build --prefix frontend

if [ ! -f frontend/dist/index.html ]; then
  echo "ERROR: frontend/dist/index.html was not produced." >&2
  exit 1
fi

echo "Render build complete: frontend/dist is ready for Flask."
