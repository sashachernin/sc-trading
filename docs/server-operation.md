# This server's forward paper experiment

Owner selections: current Linux server, start Monday **2026-10-12**, all four roles **gpt-6.1-sol**, medium reasoning, automatic bounded learning, **PAPER / SIMULATED** only. Opening 09:35, Friday exit 15:45 and Sunday discussion 12:00 in America/New_York. First opening: **2026-10-12 13:35 UTC**. Initial cash: **$1,000.00**. Synthetic history remains separate in the developer workspace.

Installed paths:

- Root-owned engine: `/opt/ai-investment-lab` with its own Python environment.
- Dedicated backend identity: `aiinvest`; persistent state `/var/lib/ai-investment-lab`.
- Protected configuration: `/etc/ai-investment-lab/engine.env`, root:aiinvest, 0640.
- PostgreSQL 16 system cluster, database `ai_investment_lab`, non-superuser role `aiinvest`; local Unix-socket peer authentication. No database password is required. Existing server user `ubuntu` cannot authenticate as `aiinvest` through peer authentication.
- Account-free Yahoo public data. No API credentials or real-money account.
- Existing Codex login is used by the separate unprivileged model service as `ubuntu`. No login token is copied into the backend or prompts.

The engine talks to `/run/ai-investment-lab-model/gateway.sock`. The gateway checks the kernel-provided peer UID against `aiinvest`, accepts only model/reasoning/schema/prompt plus bounded web mode/timeout fields, and constructs its own fresh read-only Codex commands. Two model invocations may run concurrently. Each has private temporary context and bounded output; research has a 300-second deadline, other purposes 180 seconds. Research invokes live hosted web search. See independent-research.md. Both services retain `NoNewPrivileges=true`; no passwordless sudo rule is installed. The model service's private filesystem view hides home directories, `/etc/ai-investment-lab`, backend state and engine code. Only its Codex auth directory is mounted into that view. Namespace permissions and an authenticated schema-constrained invocation were checked before activation.

Three systemd timers provide native timezone/DST scheduling and `flock` wrappers. They do not replay old firings; the worker's recovery scanner handles missed workflows and deadlines without inventing prices or dialogue.

```bash
sudo systemctl status ai-investment-lab ai-investment-lab-model
sudo systemctl list-timers 'ai-investment-lab-*'
sudo journalctl -u ai-investment-lab -u ai-investment-lab-model --since today
sudo -u aiinvest bash -c 'set -a; source /etc/ai-investment-lab/engine.env; set +a; cd /opt/ai-investment-lab; .venv/bin/python -m app.cli status'
```

Use the same protected environment for CLI `pause`, `resume --yes`, recovery and publication commands. Stop new work by pausing; existing positions retain recovery/exit handling. Stopping the worker also stops automatic liquidation, so use pause for operational investigation.

GitHub browser login is now complete as `sashachernin`; Git credential setup and push dry-run succeeded. The repository is public. The owner explicitly requested a manual first-run repository update. A private Vercel project/access policy remains unverified. `PUBLISHER_CHECKOUT` and `DEPLOYMENT_URL` remain blank and `PRIVATE_ACCESS_VERIFIED=false`. Workflows export validated snapshots locally under restricted state; no website push is performed. These hosting tasks do not block Monday's paper engine.

The installer is [scripts/install-native-server.sh](../scripts/install-native-server.sh). It targets the explicitly selected server and existing `ubuntu` Codex login, not arbitrary machines. It installs services but leaves the worker/timers disabled until manual authenticated preflight succeeds. Do not rerun it during workflows; source updates require a controlled restart. Preserve protected configuration and database history.

Back up with `sudo -u aiinvest pg_dump --format=custom --file=<protected-path> ai_investment_lab` and test restore into a separate database. Public data may be stale/unavailable and rich fundamental/news inputs are absent; see paper-trading.md. No paper profitability or continuous provider availability is promised.
