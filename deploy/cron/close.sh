#!/bin/bash
set -euo pipefail
cd /opt/ai-investment-lab
set -a
source /etc/ai-investment-lab/engine.env
set +a
exec /usr/bin/flock -n /var/lib/ai-investment-lab/locks/cron-close.lock /opt/ai-investment-lab/.venv/bin/python -m app.jobs.run_close_cycle
