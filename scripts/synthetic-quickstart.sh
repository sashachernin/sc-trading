#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli demo --weeks 3
(cd frontend && npm ci && npm run build)
.venv/bin/python scripts/check_static.py
