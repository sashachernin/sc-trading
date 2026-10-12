import csv, io, json, hashlib, re, os, shutil, tempfile
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import select
from app.config import ROOT
from app.models import *
from app.context.compiler import canonical, digest
from app.paper_trading.ledger import money, reconcile
from app.publishing.contracts import Manifest, AccountOverview
from app.meetings.orchestrator import NAMES

ALLOWED = (
    "frontend/public/data/",
    "frontend/public/transcripts/",
    "frontend/content/meetings/",
)
SECRET = re.compile(
    r'(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]+|postgres(?:ql)?://[^\s"<>]+|-----BEGIN .*PRIVATE KEY|APCA-API-SECRET-KEY|<script|javascript:|data:text/html)',
    re.I,
)


def safe_content(text):
    if SECRET.search(text):
        raise ValueError("Unsafe or secret-bearing export")
    return text


def markdown(meeting):
    data = meeting["data"]
    head = f"# {data.get('title', 'Team meeting')}\n\nAI-generated team discussion / PAPER / SIMULATED research\n\n{data.get('standfirst', '')}\n\nScheduled: {meeting['sunday']} • Source cutoff: {meeting['context']['cutoff']}\n\n"
    if meeting["status"] == "CONTENT_READY_PARTIAL":
        head += "**Partial transcript: one or more participants unavailable.**\n\n"
    for t in meeting["turns"]:
        head += f"## {NAMES[t['speaker']]['name']} — {NAMES[t['speaker']]['role']}\n\n{t['message_markdown']}\n\n"
    head += "## Recap\n\n" + data.get("recap", "") + "\n\n"
    if len(head.split()) > 2800:
        raise ValueError("Article word budget exceeded")
    return safe_content(head)


def build_files(lab, s, pub):
    cfg = lab.settings
    e = s.get(Experiment, cfg.experiment_id)
    account = s.get(Account, e.id)
    reconcile(s, account)
    cycles = list(
        s.scalars(
            select(Cycle).where(Cycle.experiment_id == e.id).order_by(Cycle.monday)
        )
    )
    meetings = list(
        s.scalars(
            select(Meeting)
            .where(
                Meeting.experiment_id == e.id,
                Meeting.status.in_(["CONTENT_READY", "CONTENT_READY_PARTIAL"]),
            )
            .order_by(Meeting.sunday.desc())
        )
    )
    positions = list(s.scalars(select(Position).where(Position.account_id == e.id)))
    fills = list(
        s.scalars(
            select(Fill)
            .join(Order, Order.id == Fill.order_id)
            .join(Position, Position.id == Order.position_id)
            .where(Position.account_id == e.id)
            .order_by(Order.created_at, Order.id)
        )
    )
    quotes = {}
    cutoffs = []
    for c in cycles:
        for snap in s.scalars(
            select(Snapshot)
            .where(Snapshot.cycle_id == c.id)
            .order_by(Snapshot.kind.desc())
        ):
            for ticker, q in snap.data["quotes"].items():
                if (
                    ticker not in quotes
                    or q["observed_at"] > quotes[ticker]["observed_at"]
                ):
                    quotes[ticker] = q
            cutoffs.append(snap.data["cutoff"])
    valuation = max(cutoffs) if cutoffs else e.start + "T00:00:00+00:00"
    invested = Decimal(0)
    basis = Decimal(0)
    position_data = []
    for p in positions:
        if p.status != "OPEN":
            continue
        q = quotes.get(p.ticker)
        if not q:
            raise ValueError("Missing supported portfolio valuation")
        value = p.quantity * Decimal(q["price"])
        invested += value
        basis += p.basis
        position_data.append(
            {
                "id": p.id,
                "ticker": p.ticker,
                "quantity": str(p.quantity),
                "basis": str(money(p.basis)),
                "value": str(money(value)),
                "status": p.status,
                "label": "PAPER / SIMULATED",
                "valuation_time": q["observed_at"],
            }
        )
    equity = account.cash + invested
    realized = account.cash + basis - Decimal(1000)
    series = [
        {
            "week": "Inception",
            "date": e.start,
            "equity": "1000.00",
            "pnl": "0.00",
            "benchmark_equity": "1000.00",
            "drawdown": "0",
        }
    ]
    peak = Decimal(1000)
    benchmark = Decimal(1000)
    for c in cycles:
        if "ending_equity" in c.data:
            val = Decimal(c.data["ending_equity"])
            peak = max(peak, val)
            benchmark *= 1 + Decimal(c.data.get("benchmark_return") or 0)
            series.append(
                {
                    "week": c.id,
                    "date": c.monday,
                    "equity": str(money(val)),
                    "pnl": c.data.get("pnl", "0.00"),
                    "benchmark_equity": str(money(benchmark)),
                    "drawdown": str((val / peak - 1) * 100),
                }
            )
    if not any(p.status == "OPEN" for p in positions):
        realized = account.cash - Decimal(1000)
    month = valuation[:7]
    monthly = sum(
        (
            Decimal(c.data.get("pnl_precise", c.data.get("pnl", "0")))
            for c in cycles
            if c.data.get("exit_cutoff", "")[:7] == month
        ),
        Decimal(0),
    )
    overview = AccountOverview(
        label="PAPER / SIMULATED",
        currency="USD",
        initial_cash="1000.00",
        equity=str(money(equity)),
        cash=str(money(account.cash)),
        invested_value=str(money(invested)),
        realized_pnl=str(money(realized)),
        unrealized_pnl=str(money(invested - basis)),
        cumulative_pnl=str(money(equity - 1000)),
        cumulative_return=str((equity / 1000 - 1) * 100),
        monthly_pnl=str(money(monthly)),
        rolling_four_week_pnl=str(
            money(
                sum(
                    (
                        Decimal(c.data.get("pnl_precise", c.data.get("pnl", "0")))
                        for c in cycles[-4:]
                    ),
                    Decimal(0),
                )
            )
        ),
        target_monthly_profit="100.00",
        target_is_experimental=True,
        completed_cycles=sum(c.status == "COMPLETED" for c in cycles),
        skipped_cycles=sum(c.status.startswith("SKIPPED") for c in cycles),
        valuation_time=valuation,
        equity_series=series,
        positions=position_data,
        fills=[
            {
                "id": f.id,
                "ticker": f.ticker,
                "quantity": str(f.quantity),
                "price": str(f.price),
                "fee": str(f.fee),
                "side": s.get(Order, f.order_id).side,
                **f.data,
            }
            for f in fills
        ],
        latest_meeting=meetings[0].id if meetings else None,
    ).model_dump(mode="json")
    files = {}

    def put(path, data):
        if not path.startswith(ALLOWED) or ".." in Path(path).parts:
            raise ValueError("Nonallowlisted export path")
        text = (
            data
            if isinstance(data, str)
            else json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
        )
        safe_content(text)
        if len(text.encode()) > 4000000:
            raise ValueError("Export file exceeds byte cap")
        files[path] = text

    put("frontend/public/data/overview.json", overview)
    index = []
    for c in cycles:
        proposals = [
            dict(
                id=p.id, run_id=p.run_id, role=s.get(AgentRun, p.run_id).role, **p.data
            )
            for p in s.scalars(
                select(Proposal).where(Proposal.cycle_id == c.id).order_by(Proposal.id)
            )
        ]
        decision = s.get(Decision, c.id)
        review = s.get(Review, c.id)
        runs = [
            {
                "id": r.id,
                "role": r.role,
                "purpose": r.purpose,
                "status": r.status,
                "manifest": r.manifest,
                "prompt_hash": r.prompt_hash,
                "model": r.metadata_.get("model"),
                "reasoning": r.metadata_.get("reasoning"),
                "prompt_excerpt": r.prompt[:1000],
                "research_summary": r.output.get("research_summary", ""),
                "abstention_reason": r.output.get("abstention_reason"),
                "investigated_tickers": r.output.get("investigated_tickers", []),
                "sources": r.output.get("sources", []),
                "web_search_mode": r.metadata_.get("web_search_mode", "disabled"),
                "web_activity": r.metadata_.get(
                    "web_activity", {"completed_calls": 0, "calls": []}
                ),
            }
            for r in s.scalars(
                select(AgentRun).where(
                    AgentRun.cycle_id == c.id, AgentRun.purpose != "MEETING_TURN"
                )
            )
        ]
        snapshots = [
            {
                "id": x.id,
                "kind": x.kind,
                "provider": x.data["provider"],
                "cutoff": x.data["cutoff"],
                "evidence": [
                    {
                        "id": q["evidence_id"],
                        "ticker": q["ticker"],
                        "observed_at": q["observed_at"],
                        "price": q["price"],
                        "redistribution": "synthetic fixture"
                        if e.synthetic
                        else "metadata only; verify provider terms",
                    }
                    for q in x.data["quotes"].values()
                ],
            }
            for x in s.scalars(select(Snapshot).where(Snapshot.cycle_id == c.id))
        ]
        stages = [
            {"stage": x.name, "completed_at": x.completed_at.isoformat()}
            for x in s.scalars(
                select(Stage).where(Stage.cycle_id == c.id).order_by(Stage.completed_at)
            )
        ]
        detail = {
            "id": c.id,
            "monday": c.monday,
            "status": c.status,
            "label": "PAPER / SIMULATED",
            "data": c.data,
            "proposals": proposals,
            "decision": decision.data if decision else None,
            "review": review.data if review else None,
            "runs": runs,
            "snapshots": snapshots,
            "fills": [f for f in overview["fills"] if f["id"].startswith(c.id + ":")],
            "timeline": stages,
            "meeting_ids": [m.id for m in meetings if m.cycle_id == c.id],
        }
        put(f"frontend/public/data/weeks/{c.id}.json", detail)
        index.append(
            {
                "id": c.id,
                "monday": c.monday,
                "status": c.status,
                "pnl": c.data.get("pnl"),
                "proposal_count": len(proposals),
                "review_available": bool(review),
            }
        )
    put("frontend/public/data/weeks/index.json", index[::-1])
    learning = [
        {
            "id": l.id,
            "role": l.role,
            "status": l.status,
            "version": l.version,
            "week_id": l.cycle_id,
            **l.data,
        }
        for l in s.scalars(
            select(Lesson).where(Lesson.experiment_id == e.id).order_by(Lesson.id)
        )
    ]
    put("frontend/public/data/learning/index.json", learning)
    meeting_index = []
    for m in meetings:
        turns = []
        for t in s.scalars(
            select(Turn).where(Turn.meeting_id == m.id).order_by(Turn.sequence)
        ):
            run = s.get(AgentRun, t.run_id)
            turns.append(
                dict(
                    id=t.id,
                    run_id=t.run_id,
                    **t.data,
                    provenance={
                        "model": run.metadata_.get("model"),
                        "manifest": run.manifest,
                        "purpose": run.purpose,
                        "usage": run.metadata_.get("usage"),
                    },
                )
            )
        if sum(len(t["message_markdown"].split()) for t in turns) > 2000:
            raise ValueError("Dialogue word budget exceeded")
        detail = {
            "id": m.id,
            "sunday": m.sunday,
            "week_id": m.cycle_id,
            "upcoming_monday": m.upcoming_monday,
            "status": m.status,
            "context": m.context,
            "data": m.data,
            "turns": turns,
        }
        article = markdown(detail)
        put(f"frontend/public/data/meetings/{m.id}.json", detail)
        put(f"frontend/content/meetings/{m.id}.md", article)
        put(f"frontend/public/transcripts/{m.id}.md", article)
        meeting_index.append(
            {
                "id": m.id,
                "sunday": m.sunday,
                "title": m.data.get("title", "Team meeting"),
                "excerpt": m.data.get("standfirst", ""),
                "status": m.status,
                "week_id": m.cycle_id,
                "participants": list(NAMES.values()),
                "reading_minutes": max(1, len(article.split()) // 200),
            }
        )
    put("frontend/public/data/meetings/index.json", meeting_index)
    jobs = list(s.scalars(select(Job).where(Job.experiment_id == e.id)))
    previous = s.scalars(
        select(Publication)
        .where(Publication.experiment_id == e.id, Publication.revision < pub.revision)
        .order_by(Publication.revision.desc())
    ).first()
    operations = {
        "observed_at": pub.data["created_at"],
        "paused": e.paused,
        "worker_status": "Snapshot observation; live status available only through Linux CLI",
        "queue": {
            state: sum(j.status == state for j in jobs)
            for state in ("QUEUED", "RUNNING", "COMPLETED", "FAILED")
        },
        "incidents": [
            {
                "id": i.id,
                "category": i.category,
                "summary": i.summary,
                "observed_at": i.created_at.isoformat(),
            }
            for i in s.scalars(select(Incident).where(Incident.experiment_id == e.id))
        ],
        "audit": [
            {"action": a.action, "data": a.data, "created_at": a.created_at.isoformat()}
            for a in s.scalars(select(Audit).where(Audit.experiment_id == e.id))
        ],
        "settings": {
            "provider": cfg.market_provider,
            "synthetic": e.synthetic,
            "learning_mode": cfg.learning_mode,
            "site_visibility": cfg.site_visibility,
            "private_access_verified": cfg.private_access_verified,
            "max_stock_allocation": cfg.max_stock_allocation,
            "max_deployed": cfg.max_deployed,
            "start": e.start,
            "end": e.end,
            "participants": NAMES,
            "schedule": {
                "Monday": "09:35 America/New_York",
                "Friday": "15:45 America/New_York",
                "Sunday": "12:00 America/New_York",
            },
            "meeting_turn_limit": 11,
            "active_memory_cap": 12,
            "models": {
                r: cfg.model_for(r)
                or (
                    "synthetic-fixture-v1"
                    if cfg.codex_mode == "fake"
                    else "UNCONFIGURED"
                )
                for r in NAMES
            },
        },
        "meetings": [
            {
                "id": mm.id,
                "sunday": mm.sunday,
                "status": mm.status,
                "turn_count": mm.data.get("turn_count", 0),
                "unavailable": mm.data.get("unavailable", []),
            }
            for mm in s.scalars(
                select(Meeting)
                .where(Meeting.experiment_id == e.id)
                .order_by(Meeting.sunday.desc())
            )
        ],
        "previous_delivery": {"snapshot_id": previous.id, "status": previous.status}
        if previous
        else None,
    }
    put("frontend/public/data/operations.json", operations)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["label", "week", "status", "net_pnl_usd"])
    for c in cycles:
        writer.writerow(["PAPER / SIMULATED", c.id, c.status, c.data.get("pnl", "")])
    put("frontend/public/data/performance.csv", output.getvalue())
    manifest = Manifest(
        schema_version="1",
        snapshot_id=pub.id,
        source_revision=pub.revision,
        experiment_id=e.id,
        label="PAPER / SIMULATED",
        synthetic=e.synthetic,
        created_at=pub.data["created_at"],
        source_cutoff=max([valuation] + [m.context["cutoff"] for m in meetings]),
        valuation_time=valuation,
        next_expected_publication="Next scheduled Monday / Friday / Sunday workflow, America/New_York",
        files=[
            {
                "path": p,
                "sha256": hashlib.sha256(t.encode()).hexdigest(),
                "bytes": len(t.encode()),
                "schema_version": "1",
            }
            for p, t in sorted(files.items())
        ],
    ).model_dump(mode="json")
    put("frontend/public/data/manifest.json", manifest)
    return files, manifest


def export(lab):
    cfg = lab.settings
    with lab.lock():
        with lab.sessions.begin() as s:
            # PostgreSQL repeatable read freezes the revision and every exported record.
            if lab.engine.dialect.name == "postgresql":
                s.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            e = s.get(Experiment, cfg.experiment_id)
            pub = s.scalar(
                select(Publication).where(
                    Publication.experiment_id == e.id,
                    Publication.revision == e.revision,
                )
            )
            if not pub:
                id = f"{e.id}-r{e.revision}"
                pub = Publication(
                    id=id,
                    experiment_id=e.id,
                    revision=e.revision,
                    status="EXPORTING",
                    data={"created_at": utcnow().isoformat()},
                )
                s.add(pub)
                s.flush()
            frozen_dir = cfg.state_dir / "exports" / pub.id
            if frozen_dir.exists() and pub.status != "EXPORTING":
                if cfg.materialize_local_export:
                    for prefix in ALLOWED:
                        target = ROOT / prefix
                        source = frozen_dir / prefix
                        if target.exists():
                            shutil.rmtree(target)
                        if source.exists():
                            shutil.copytree(source, target)
                return pub
            files, manifest = build_files(lab, s, pub)
            frozen_dir.mkdir(parents=True, exist_ok=True)
            for path, text in files.items():
                target = frozen_dir / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            # Local developer checkout is a preview view; Git publishing uses its own checkout.
            if cfg.materialize_local_export:
                for prefix in ALLOWED:
                    target = ROOT / prefix
                    source = frozen_dir / prefix
                    if target.exists():
                        shutil.rmtree(target)
                    if source.exists():
                        shutil.copytree(source, target)
            pub.status = "VALIDATED"
            pub.data = dict(
                pub.data, manifest=manifest, export_directory=str(frozen_dir.resolve())
            )
        return pub
