#!/usr/bin/env bash
#
# Root-level start script for Railpack/Railway.
#
# NOTE: CashPulse is a monorepo containing two independent services:
#   - backend/   Django + DRF API (backend/Dockerfile, backend/requirements.txt)
#   - frontend/  React + TypeScript SPA (frontend/Dockerfile, frontend/package.json)
#
# Railpack cannot auto-detect a single service to build at the repo root
# because there are two separate apps, each with its own Dockerfile and
# dependency manifest. The recommended setup is to deploy this repo as
# TWO separate Railway services, each with its Root Directory set to
# `backend` or `frontend` respectively, so each one builds from its own
# Dockerfile:
#
#   Service "cashpulse-backend"  -> Root Directory: backend  -> backend/Dockerfile
#   Service "cashpulse-frontend" -> Root Directory: frontend -> frontend/Dockerfile
#
# Until that split is configured, this script lets the repo boot as a
# single service by starting the Django backend (the API the frontend
# depends on) directly from the repo root.

set -euo pipefail

cd "$(dirname "$0")/backend"

PORT="${PORT:-8000}"

echo "=================================================================="
echo " CashPulse monorepo detected."
echo " This repo contains two independent services (backend/, frontend/)."
echo " For production use, split them into two Railway services, each"
echo " with its Root Directory set to 'backend' or 'frontend'."
echo "=================================================================="
echo "Starting Django backend on 0.0.0.0:${PORT} ..."

if command -v gunicorn >/dev/null 2>&1; then
    echo "Command: gunicorn config.wsgi:application --bind 0.0.0.0:${PORT}"
    exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT}"
else
    echo "Command: python manage.py runserver 0.0.0.0:${PORT}"
    exec python manage.py runserver "0.0.0.0:${PORT}"
fi
