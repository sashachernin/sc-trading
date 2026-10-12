# AI Trading Firm Dashboard

Read-only static web app for tracking the AI trading firm's research, proposals, manager decisions, simulated trades, performance, learning updates and Sunday discussions.

**PAPER / SIMULATED:** all displayed trades use a simulated account.

This repository contains the Next.js dashboard and curated published snapshots only. The trading engine, database, agent prompts, scheduling and credentials run separately on the Linux server. Browsing the dashboard does not run agents or place orders.

## Run locally

Requires Node.js 22 and npm.

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000.

## Build and deploy

```bash
cd frontend
npm ci
npm run build
```

The build validates snapshot schemas and file hashes, then generates the static website in `frontend/out/`. Preview it with `npm run start` from `frontend/`.

For Vercel, import this repository and set:

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `out` |
| Production branch | `main` |

Configure website access in the hosting provider. No database, brokerage, model or server credentials belong in this repository or the hosting environment.

## Published results

The Linux engine exports validated snapshots into `frontend/public/data/`, transcript downloads into `frontend/public/transcripts/`, and meeting content into `frontend/content/meetings/`. Each coherent snapshot has a manifest with its revision, file sizes and hashes. The dashboard displays the last published observations and their timestamps; it remains usable when the Linux server is offline.

The current October 12, 2026 opening is the one-time replacement of the failed morning research: both researchers browsed independently, the manager selected a $100 AMZN allocation, and the simulated account opened a position. Original morning records remain in the published audit data. See the Weeks page for the research, sources, decision and fill.

Future snapshots are generated on Linux after scheduled workflows. Updating GitHub and deploying the website are separate steps; the displayed snapshot identifies which results are actually published.

## Repository layout

- `frontend/app/`: dashboard pages and statically generated week/meeting routes.
- `frontend/components/`: charts, tables and other display components.
- `frontend/lib/`: snapshot readers, types and validation schemas.
- `frontend/public/`: published data and downloadable assets.
- `frontend/content/`: curated meeting articles.
- `.github/workflows/`: static build and snapshot validation.
