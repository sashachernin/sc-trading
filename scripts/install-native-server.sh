#!/bin/bash
# Install this server's paper engine; activate workflows only after separate preflight succeeds.
set -euo pipefail
project_dir=/home/ubuntu/projects/sc-trading
install_dir=/opt/ai-investment-lab
id aiinvest >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/ai-investment-lab --shell /usr/sbin/nologin aiinvest
install -d -o aiinvest -g aiinvest -m 700 /var/lib/ai-investment-lab/{runs,exports,locks}
install -d -o root -g aiinvest -m 750 /etc/ai-investment-lab
install -d -o root -g root -m 755 "$install_dir" /usr/local/libexec
tar --exclude='./.git' --exclude='./.venv' --exclude='./state' --exclude='./.env' --exclude='./frontend/node_modules' --exclude='./frontend/.next' --exclude='./frontend/out' --exclude='__pycache__' --exclude='./.pytest_cache' -C "$project_dir" -cf /tmp/lab-native-source.tar .
tar -C "$install_dir" -xf /tmp/lab-native-source.tar
mkdir -p "$install_dir/.venv"
cp -a "$project_dir/.venv/." "$install_dir/.venv/"
"$install_dir/.venv/bin/python" -m pip install --no-deps -e "$install_dir" >/tmp/lab-native-install.log
chown -R root:root "$install_dir"
chmod -R go-w "$install_dir"
install -o root -g root -m 755 "$project_dir/deploy/launchers/model-gateway.py" /usr/local/libexec/lab-model-gateway.py
install -o root -g root -m 755 "$project_dir/deploy/launchers/model-client.py" /usr/local/bin/lab-codex
install -o root -g root -m 755 "$project_dir/scripts/limited_exec.py" /usr/local/libexec/lab-limited-exec.py
install -o root -g root -m 755 /home/ubuntu/.local/bin/codex /usr/local/libexec/lab-codex-binary
install -o root -g root -m 644 "$project_dir/backend/app/codex_runner/provenance.py" /usr/local/libexec/lab_model_events.py
install -o root -g root -m 755 /home/ubuntu/.codex/packages/standalone/current/bin/codex-code-mode-host /usr/local/libexec/codex-code-mode-host
systemctl enable --now postgresql
if [ "$(runuser -u postgres -- psql -Atqc "SELECT 1 FROM pg_roles WHERE rolname='aiinvest'")" != "1" ]; then
 runuser -u postgres -- createuser --no-superuser --no-createdb --no-createrole aiinvest
fi
if [ "$(runuser -u postgres -- psql -Atqc "SELECT 1 FROM pg_database WHERE datname='ai_investment_lab'")" != "1" ]; then
 runuser -u postgres -- createdb -O aiinvest ai_investment_lab
fi
runuser -u postgres -- psql -d ai_investment_lab -c 'REVOKE ALL ON DATABASE ai_investment_lab FROM PUBLIC; REVOKE CREATE ON SCHEMA public FROM PUBLIC;' >/dev/null
if [ ! -e /etc/ai-investment-lab/engine.env ]; then
 sed -e 's|^DATABASE_URL=.*|DATABASE_URL="postgresql+psycopg://aiinvest@/ai_investment_lab?host=/var/run/postgresql"|' \
     -e 's|^CODEX_BINARY=.*|CODEX_BINARY=/usr/local/bin/lab-codex|' \
     -e 's|^CODEX_AUTH_HOME=.*|CODEX_AUTH_HOME=/run/lab-codex-auth|' \
     "$project_dir/deploy/forward.env.example" > /etc/ai-investment-lab/engine.env
 chown root:aiinvest /etc/ai-investment-lab/engine.env
 chmod 640 /etc/ai-investment-lab/engine.env
fi
install -o root -g root -m 644 "$project_dir"/deploy/systemd/ai-investment-lab*.service "$project_dir"/deploy/systemd/ai-investment-lab*.timer /etc/systemd/system/
systemctl daemon-reload
# Model gateway is unprivileged; no passwordless sudo or privilege relaxation.
systemctl start ai-investment-lab-model
runuser -u aiinvest -- bash -c 'set -a; source /etc/ai-investment-lab/engine.env; set +a; cd /opt/ai-investment-lab; .venv/bin/python -m alembic upgrade head; .venv/bin/python -m app.cli init; .venv/bin/python -m app.cli preflight'
echo 'Installed. Worker and workflow timers remain disabled until authenticated isolation preflight succeeds.'
