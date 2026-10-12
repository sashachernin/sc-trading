# Native Linux deployment

The current owner-selected server is installed using the unprivileged socket gateway and native systemd timers described in [server-operation.md](server-operation.md). [install-native-server.sh](../scripts/install-native-server.sh) records that deployment. The generic manual instructions below describe alternate server setup.

Install Python 3.12/venv, PostgreSQL 16+, Git, Node.js 22/npm, util-linux/flock and a cron implementation with verified timezone support. A host administrator performs account/service setup. Keep these commands reviewable; do not run them blindly on a shared host.

```bash
sudo useradd --system --create-home --home-dir /var/lib/ai-investment-lab --shell /bin/bash aiinvest
sudo install -d -o aiinvest -g aiinvest -m 700 /var/lib/ai-investment-lab/{locks,runs,exports,codex-auth}
sudo install -d -o root -g aiinvest -m 750 /etc/ai-investment-lab
# Install this repository at /opt/ai-investment-lab, owned by root/readable by aiinvest.
cd /opt/ai-investment-lab
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
```

Provision the DB using `deploy/postgres.sql`, an interactive password and SCRAM `pg_hba.conf` restricted to the service host. Use TLS for a remote DB. The application role owns its schema, not other databases; revoke public database access. Configure `/etc/ai-investment-lab/engine.env` (root:aiinvest, mode 640) with PostgreSQL URL, distinct experiment ID, start date, state path `/var/lib/ai-investment-lab`, real provider credentials, Codex settings and `MATERIALIZE_LOCAL_EXPORT=false`. Keep separate credentials for the publisher identity.

```bash
# Use the protected environment, without displaying it.
sudo -u aiinvest bash -c 'set -a; source /etc/ai-investment-lab/engine.env; set +a; cd /opt/ai-investment-lab; .venv/bin/alembic upgrade head; .venv/bin/python -m app.cli init; .venv/bin/python -m app.cli preflight'
sudo install -m 644 deploy/systemd/ai-investment-lab.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-investment-lab
sudo systemctl status ai-investment-lab
sudo journalctl -u ai-investment-lab -f
```

Configure a distinct isolated model-execution identity and restricted launcher before real AI work. The worker's `ProtectSystem`, `ProtectHome`, `NoNewPrivileges`, private tmp, restrictive umask, memory/task/file limits and state-only write permissions provide service hardening, not full separation of model-readable secrets. See `codex-runner.md`.

Install three cron wrappers from `deploy/cron/` only after checking timezone behavior. The supplied `CRON_TZ` entries require a supporting implementation such as Cronie. Debian cron may ignore `CRON_TZ`; exporting `TZ` affects the process but does not necessarily change scheduler firing. On those hosts either install a verified supporting cron or schedule UTC every minute with an audited timezone-aware dispatcher. Do not install the supplied schedule under unverified cron and claim DST safety. Unit tests check New York UTC offset changes; an actual host trigger test must also be performed.

Create a separate Git publisher checkout under `/var/lib/ai-investment-lab/publisher`; it needs its own identity/credential helper and a locked Node toolchain. `PUBLISHER_CHECKOUT` must not point at the engine source. Verify synthetic push, build and access protection before enabling real-data publication.

Back up with `pg_dump --format=custom` to encrypted restricted storage, and test `pg_restore` into a separate database. Pause new work, keep exit recovery available, restore DB, run ledger reconciliation/status and compare IDs before resuming. Keep backup credentials outside model workspaces. See operations for failed/missed weeks and restoration.
