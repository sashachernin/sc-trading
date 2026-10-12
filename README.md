# AI Investment Lab

A native Linux research engine and read-only Next.js dashboard for an autonomous, year-long **PAPER / SIMULATED** stock experiment. Four roles independently research, select, review and discuss a cash-funded $1,000 paper account. The $100 net monthly profit goal in month 12 is an experimental objective, not a forecast or promise.

**Current default:** deterministic synthetic market data and a fake Codex executable. Three demonstration weeks and their Sunday discussions are included. No real-money broker order API exists. See [verification and implementation status](docs/verification.md) for executed checks and remaining production limitations.

## Latest forward result

[Monday, October 12, 2026](docs/results/2026-10-12.md): opening research completed with **HOLD_CASH**. Both researchers abstained because no market observations passed validation. Paper cash remains **$1,000.00**, with no positions or trades. The committed dashboard data is the real forward snapshot `paper-2026-10-12-r6`; the synthetic demonstration remains a separate local experiment.

## Quickstart

Requirements: Linux, Python 3.12+, Python venv/pip support, Node.js 20.9+ (22 recommended), npm and Git. Production uses PostgreSQL; the local demo uses SQLite so credentials are unnecessary.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
cp .env.example .env
alembic upgrade head
python -m app.cli demo --weeks 3
python -m app.cli status
cd frontend
npm ci
npm run build
python3 -m http.server 3000 --directory out --bind 127.0.0.1
```

Open **http://localhost:3000**. This serves the actual static export; Linux research services can be stopped and the website remains readable. For frontend development use `npm run dev`. The demo is idempotent: rerunning it preserves fills, accepted dialogue and overlays. Dates are fixture dates, not current market observations. A new synthetic experiment requires a distinct `EXPERIMENT_ID` and `EXPERIMENT_START` in `.env`.

If `venv` fails on Ubuntu, install `python3.12-venv` and `python3-pip` using your host's package manager. An existing environment can install the locked dependencies directly.

## Verify

```bash
source .venv/bin/activate
pytest -q
python scripts/check_static.py
python -m app.cli preflight
python -m app.cli publish-site --dry-run
```

`pytest` uses temporary synthetic databases and fresh fake subprocesses. `check_static.py` checks built article/week routes and downloads. `npm run build` verifies the entire manifest's hashes before generating pages. GitHub CI additionally runs migrations and the demo against PostgreSQL. The real GitHub/Vercel smoke test requires configured accounts and is documented separately.

## Operate

```bash
python -m app.cli run-open-cycle --date 2026-10-12
python -m app.cli run-close-cycle --date 2026-10-16
python -m app.cli run-sunday-meeting --date 2026-10-18
python -m app.cli worker-once
python -m app.jobs.worker
python -m app.cli set-setting --key max_stock_allocation --value .25 --yes
python -m app.cli pause
python -m app.cli resume --yes
python -m app.cli retry --id '<job-id>'
python -m app.cli recover-exit --date '<date-in-the-original-week>' --yes
python -m app.cli approve-lesson --id '<lesson-id>' --yes
python -m app.cli rollback-lesson --id '<lesson-id>' --yes
python -m app.cli publish-site --dry-run
python -m app.cli publish-site
```

Cycle commands enqueue durable jobs; the worker executes them. Cron modules are thin wrappers around the same services. Publication retries use committed history, with no new AI speech or financial effects. Consequential manual commands require `--yes` and produce audit records. Pausing gates new research and meetings while permitting liquidation.

## Enable a forward paper experiment

The owner-selected forward start is **Monday, October 12, 2026**, with **gpt-6.1-sol** for all four roles and medium reasoning. [deploy/forward.env.example](deploy/forward.env.example) contains this configuration with account-free Yahoo public data. The native deployment on this server uses protected configuration in `/etc/ai-investment-lab/engine.env`; see [server operation](docs/server-operation.md). The synthetic demonstration retains its separate history and dates.

1. Follow [native Linux deployment](docs/native-linux-deployment.md): dedicated unprivileged service user, PostgreSQL, migrations, persistent state, worker and three timezone-aware systemd timers (or verified cron entries).
2. Create a separate experiment ID and set the start date. Set `MARKET_PROVIDER=yahoo` for account-free personal research, or `alpaca` with protected API credentials. Review the configured common-stock universe and provider limitations. Read [market-data assumptions](docs/paper-trading.md).
3. Set `CODEX_MODE=real`, configure all four model IDs, install/authenticate Codex as the isolated execution identity, and run preflight. The runner was checked against `codex-cli 0.162.1`; no model is silently substituted. See [runner deployment](docs/codex-runner.md).
4. Configure a separate publisher checkout and scoped Git identity. Import the private GitHub repository into Vercel with `frontend/` as the project root. See [GitHub/Vercel deployment](docs/github-vercel-deployment.md).
5. Default visibility is private. Verify hosting access on **production domains, deployment/preview URLs, articles, JSON and transcripts** with a synthetic deployment, then set `PRIVATE_ACCESS_VERIFIED=true`. Export validation does not establish hosting privacy. Publishing is blocked until that operator acceptance or explicit public configuration.
6. Run the full synthetic smoke test before enabling real-data publication. A Git push and a verified Vercel deployment are reported separately.

Credentials belong in protected Linux configuration; none belong in frontend variables, Git remote URLs, prompts, logs or commits. Yahoo public data needs no account or API key. This server uses its existing Codex login and local PostgreSQL peer authentication. GitHub publishing and private Vercel hosting still require authenticated access; no remote deployment is claimed until verified.

## Repository

- `backend/app/`: contracts, bounded context, subprocesses, market data, paper ledger, workflows, meetings, durable queue, publishing and CLI.
- `backend/migrations/`: Alembic schema migrations. PostgreSQL is the production source of truth.
- `frontend/`: Next.js App Router, React/TypeScript/Tailwind static dashboard and committed synthetic snapshots.
- `prompts/`, `schemas/`: stable role prompts and versioned output/export contracts.
- `deploy/`: systemd worker, cron wrappers and database provisioning template.
- `docs/`: architecture, research methodology, recovery, deployment and UI walkthrough.

## Documentation

[Architecture](docs/architecture.md) · [Agent contracts](docs/agent-contracts.md) · [Context and memory](docs/context-and-memory.md) · [Learning methodology](docs/learning-methodology.md) · [Paper accounting](docs/paper-trading.md) · [Team meetings](docs/team-meetings.md) · [Website publisher](docs/website-publisher.md) · [Operations](docs/operations.md) · [UI walkthrough](docs/ui-walkthrough.md) · [Verification](docs/verification.md)
