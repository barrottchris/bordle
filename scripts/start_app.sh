#!/usr/bin/env sh
set -eu

# Run once in the service process before Gunicorn imports app.py and loads map data.
python scripts/build_map_data.py

exec gunicorn --bind "0.0.0.0:${PORT:-8000}" app:app
