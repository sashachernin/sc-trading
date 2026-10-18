# AI Trading Firm Dashboard

Read-only static web app for tracking the AI trading firm's research, proposals, manager decisions, simulated trades, performance, learning updates and Sunday discussions.

**PAPER / SIMULATED:** all displayed trades use a simulated account.

New purchases use whole shares only. Share counts round down after allowing for costs, and unused allocations remain in cash. Historical fractional trades remain in the records.

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
| Framework preset | **Other** (static export) |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `out` |
| Production branch | `main` |

The committed `frontend/vercel.json` sets `framework: null` so Vercel serves the exported `out/` files as a static site. Selecting the Next.js preset together with `out` can cause a missing `routes-manifest.json` error.

Configure website access in the hosting provider. No database, brokerage, model or server credentials belong in this repository or the hosting environment.

## Published results

The Linux engine exports validated snapshots into `frontend/public/data/`, transcript downloads into `frontend/public/transcripts/`, and meeting content into `frontend/content/meetings/`. Each coherent snapshot has a manifest with its revision, file sizes and hashes. The dashboard displays the last published observations and their timestamps; it remains usable when the Linux server is offline.

The current October 12, 2026 opening is the one-time replacement of the failed morning research: both researchers browsed independently, the manager selected a $100 AMZN allocation, and the simulated account opened a position. Original morning records remain in the published audit data. See the Weeks page for the research, sources, decision and fill.

The Linux server refreshes holdings and account profit/loss once each trading day at **12:45 p.m. New York time**, skipping exchange holidays. The team meeting starts every Sunday at **08:00 UTC**, year-round. It also publishes Monday, Friday and Sunday workflow results. Valuation updates do not run new research or change trades. Updating GitHub and deploying the website are separate steps; the displayed snapshot identifies which results are actually published.

## Repository layout

- `frontend/app/`: dashboard pages and statically generated week/meeting routes.
- `frontend/components/`: charts, tables and other display components.
- `frontend/lib/`: snapshot readers, types and validation schemas.
- `frontend/public/`: published data and downloadable assets.
- `frontend/content/`: curated meeting articles.
- `.github/workflows/`: static build and snapshot validation.

## CEO opening messages

On the Linux server, edit `ceo/CEO_MESSAGES.md` in the project workspace before Sunday 08:00 UTC. It contains dated placeholders for the remaining 51 meetings, starting October 25, 2026. The selected message opens that week’s published discussion and is supplied to every participant; future drafts stay local. Blank placeholders are skipped. Edits after a meeting starts do not change its frozen opening.
