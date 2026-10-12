from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import calendar, fcntl, uuid
from sqlalchemy import select, update, func
from app.models import *
from app.config import Settings
from app.agents.contracts import CONTRACTS
from app.context.compiler import PromptCompiler, digest
from app.codex_runner.runner import CodexRunner, RunnerError
from app.market_data.providers import (
    provider,
    screen,
    eligible_week,
    iso,
    executable_packet,
)
from app.paper_trading.ledger import reconcile, validate_decision, buy, sell, money
from app.learning.gate import apply

NY = ZoneInfo("America/New_York")
ROLES = ["researcher_a", "researcher_b", "manager", "analyst"]


def scheduled(day, hour, minute=0):
    return iso(
        datetime.combine(day, datetime.min.time()).replace(
            hour=hour, minute=minute, tzinfo=NY
        )
    )


def end_date(start):
    year = start.year + 1
    return start.replace(
        year=year, day=min(start.day, calendar.monthrange(year, start.month)[1])
    )


class Lab:
    def __init__(self, settings=None):
        self.settings = settings or Settings()
        self.engine, self.sessions = connect(self.settings)
        from app.operator_settings import effective

        self.settings = effective(self.engine, self.sessions, self.settings)
        self.compiler = PromptCompiler(self.settings)
        self.runner = CodexRunner(self.settings)

    def initialize(self):
        with self.sessions.begin() as s:
            if not s.get(Experiment, self.settings.experiment_id):
                e = Experiment(
                    id=self.settings.experiment_id,
                    start=str(self.settings.experiment_start),
                    end=str(end_date(self.settings.experiment_start)),
                    synthetic=self.settings.market_provider == "synthetic",
                    paused=False,
                    revision=0,
                )
                s.add(e)
                s.flush()
                s.add(Account(id=e.id, cash=Decimal("1000")))
                s.flush()
                s.add(
                    Ledger(
                        id=e.id + ":initial",
                        account_id=e.id,
                        amount=Decimal("1000"),
                        kind="PAPER_INITIAL_CAPITAL",
                    )
                )
            e = s.get(Experiment, self.settings.experiment_id)
            if e.synthetic != (self.settings.market_provider == "synthetic"):
                raise ValueError("Experiment provider mode is immutable")

    @contextmanager
    def lock(self):
        locks = self.settings.state_dir / "locks"
        locks.mkdir(parents=True, exist_ok=True)
        with (locks / (digest(self.settings.experiment_id) + ".lock")).open("w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            # PostgreSQL advisory lock also protects multiple hosts sharing this DB.
            with self.engine.connect() as conn:
                key = int(digest(self.settings.experiment_id)[:15], 16)
                if self.engine.dialect.name == "postgresql":
                    conn.exec_driver_sql("SELECT pg_advisory_lock(%s)", (key,))
                    conn.commit()
                try:
                    yield
                finally:
                    if self.engine.dialect.name == "postgresql":
                        conn.exec_driver_sql("SELECT pg_advisory_unlock(%s)", (key,))
                        conn.commit()

    def fence(self, s):
        active = getattr(self, "active_lease", None)
        if active:
            job = s.get(Job, active[0])
            if not job or job.status != "RUNNING" or job.lease != active[1]:
                raise ValueError("Stale worker lease; transaction fenced")

    def bump(self, s):
        self.fence(s)
        s.execute(
            update(Experiment)
            .where(Experiment.id == self.settings.experiment_id)
            .values(revision=Experiment.revision + 1)
        )

    def cycle(self, s, monday):
        id = f"{self.settings.experiment_id}-{monday}"
        c = s.get(Cycle, id)
        if not c:
            c = Cycle(
                id=id,
                experiment_id=self.settings.experiment_id,
                monday=str(monday),
                status="PLANNED",
                data={},
            )
            s.add(c)
            s.flush()
        return c

    def allowed(self, s, day):
        e = s.get(Experiment, self.settings.experiment_id)
        return not e.paused and e.start <= str(day) < e.end

    def invoke(
        self, role, purpose, current, cutoff, cycle_id=None, run_id=None, max_attempts=3
    ):
        contract = CONTRACTS[purpose]
        run_id = run_id or str(uuid.uuid4())
        with self.sessions() as s:
            existing = s.get(AgentRun, run_id)
            if existing and existing.status == "COMPLETED":
                return existing.output, run_id
            prompt, manifest = self.compiler.compile(
                s, role, purpose, current, contract, cutoff
            )
        current = dict(current, lesson_ids=manifest["lesson_ids"])
        attempts = []
        for attempt in range(max_attempts):
            try:
                output, metadata = self.runner.run(
                    role, purpose, prompt, contract, current
                )
                import jsonschema

                jsonschema.validate(output, contract.model_json_schema())
                self.validate_refs(output, purpose, current, role)
                metadata["attempts"] = attempts + [
                    {"attempt": attempt + 1, "status": "COMPLETED"}
                ]
                break
            except RunnerError as exc:
                attempts.append({"attempt": attempt + 1, "category": exc.category})
                if (
                    exc.category not in ("RATE_LIMIT", "TIMEOUT", "PROCESS")
                    or attempt == max_attempts - 1
                ):
                    with self.sessions.begin() as s:
                        s.merge(
                            AgentRun(
                                id=run_id,
                                cycle_id=cycle_id,
                                role=role,
                                purpose=purpose,
                                status="FAILED",
                                prompt=prompt,
                                prompt_hash=digest(prompt),
                                manifest=manifest,
                                output={},
                                metadata_={
                                    "attempts": attempts,
                                    "failure": exc.category,
                                },
                            )
                        )
                        self.bump(s)
                    raise
        with self.sessions.begin() as s:
            s.merge(
                AgentRun(
                    id=run_id,
                    cycle_id=cycle_id,
                    role=role,
                    purpose=purpose,
                    status="COMPLETED",
                    prompt=prompt,
                    prompt_hash=digest(prompt),
                    manifest=manifest,
                    output=output,
                    metadata_=metadata,
                )
            )
            self.bump(s)
        return output, run_id

    def validate_refs(self, out, purpose, current, role):
        if purpose == "RESEARCH":
            packet = current["market"]
            allowed = {q["evidence_id"] for q in packet["quotes"].values()}
            browsing = (
                self.settings.independent_web_research
                and self.settings.codex_mode == "real"
            )
            sources = out.get("sources", [])
            if not browsing and sources:
                raise RunnerError("VALIDATION")
            if browsing:
                from app.market_data.providers import parse

                allowed |= {s["id"] for s in sources}
                for source in sources:
                    if not source["id"].startswith("web-" + role + "-"):
                        raise RunnerError("VALIDATION")
                    if source["published_at"] is not None:
                        try:
                            if parse(source["published_at"]) > parse(packet["cutoff"]):
                                raise RunnerError("VALIDATION")
                        except (ValueError, TypeError):
                            raise RunnerError("VALIDATION")
                if not out.get("research_summary") or not out.get(
                    "investigated_tickers"
                ):
                    raise RunnerError("VALIDATION")
                if not set(out["investigated_tickers"]) <= set(
                    self.settings.universe.split(",")
                ):
                    raise RunnerError("VALIDATION")
                if out["candidates"] and len(sources) < 2:
                    raise RunnerError("VALIDATION")
            if (
                out["role"] != role
                or out["cutoff"] != packet["cutoff"]
                or out["snapshot_id"] != packet["id"]
            ):
                raise RunnerError("VALIDATION")
            for c in out["candidates"]:
                if (
                    c["ticker"]
                    not in (
                        self.settings.universe.split(",")
                        if browsing
                        else packet["quotes"]
                    )
                    or not set(c["evidence_ids"]) <= allowed
                ):
                    raise RunnerError("VALIDATION")
        elif purpose in ("REVIEW", "MEETING_TURN"):
            if not set(out["evidence_ids"]) <= set(current["evidence_ids"]):
                raise RunnerError("VALIDATION")
        if purpose == "MEETING_TURN":
            if (
                any(out[k] != current[k] for k in ("meeting_id", "sequence", "phase"))
                or out["speaker"] != role
            ):
                raise RunnerError("VALIDATION")
            if not set(out["reply_to_turn_ids"]) <= {
                t["id"] for t in current["transcript"]
            }:
                raise RunnerError("VALIDATION")
            if current["sequence"] in (5, 7, 9):
                if (
                    current["remaining"]
                    and out["next_speaker"] not in current["remaining"]
                ):
                    raise RunnerError("VALIDATION")
                if not current["remaining"] and out["next_speaker"] is not None:
                    raise RunnerError("VALIDATION")
            elif out["next_speaker"] is not None:
                raise RunnerError("VALIDATION")
            if "<" in out["message_markdown"] or "](" in out["message_markdown"]:
                raise RunnerError("VALIDATION")

    def incident(self, category, summary):
        with self.sessions.begin() as s:
            s.add(
                Incident(
                    id=str(uuid.uuid4()),
                    experiment_id=self.settings.experiment_id,
                    category=category,
                    summary=summary,
                )
            )
            self.bump(s)

    def stage_done(self, s, c, name):
        return s.get(Stage, c.id + ":" + name) is not None

    def mark(self, s, c, name):
        s.add(Stage(id=c.id + ":" + name, cycle_id=c.id, name=name))
        self.bump(s)

    def request_publish(self):
        from app.jobs.queue import enqueue

        with self.sessions.begin() as s:
            e = s.get(Experiment, self.settings.experiment_id)
            enqueue(
                s,
                self.settings,
                "PUBLISH",
                {"revision": e.revision},
                f"publish:{e.revision}",
                priority=20,
            )

    def open(self, monday, now=None, *, replace_failed_once=False):
        if monday.weekday() != 0:
            raise ValueError("Opening date must be Monday")
        now = now or utcnow()
        cfg = self.settings
        if cfg.market_provider != "synthetic" and (
            now.astimezone(NY).date() != monday
            or now < datetime.fromisoformat(scheduled(monday, 9, 35))
        ):
            raise ValueError("Forward opening must run in the Monday entry window")
        with self.lock():
            with self.sessions.begin() as s:
                c = self.cycle(s, monday)
                if replace_failed_once:
                    if (
                        now.astimezone(NY).date() != monday
                        or now >= datetime.fromisoformat(scheduled(monday, 15, 45))
                        or c.status != "HOLD_CASH"
                        or c.data.get("one_time_replacement")
                        or not self.stage_done(s, c, "PURCHASES")
                        or s.scalar(
                            select(func.count())
                            .select_from(Position)
                            .where(Position.account_id == cfg.experiment_id)
                        )
                        or s.scalar(
                            select(func.count())
                            .select_from(Proposal)
                            .where(Proposal.cycle_id == c.id)
                        )
                    ):
                        raise ValueError(
                            "Replacement requires an unreplaced, cash-only failed Monday cycle during market hours"
                        )
                    old_decision = s.get(Decision, c.id)
                    if old_decision and old_decision.data.get("allocations"):
                        raise ValueError("Cannot replace an allocated decision")
                    prior_stages = list(
                        s.scalars(select(Stage).where(Stage.cycle_id == c.id))
                    )
                    saved = s.get(Snapshot, c.id + ":entry")
                    archive = {
                        "cycle_id": c.id,
                        "authorized_at": iso(now),
                        "authorization": "User requested replacement of failed morning research, just once",
                        "original_status": c.status,
                        "original_data": c.data,
                        "original_decision": old_decision.data
                        if old_decision
                        else None,
                        "original_decision_run_id": old_decision.run_id
                        if old_decision
                        else None,
                        "original_stages": [
                            {
                                "name": stage.name,
                                "completed_at": iso(stage.completed_at),
                            }
                            for stage in prior_stages
                        ],
                        "original_snapshot": saved.data if saved else None,
                    }
                    s.add(
                        Audit(
                            experiment_id=cfg.experiment_id,
                            action="replace-failed-open-once",
                            data=archive,
                        )
                    )
                    if old_decision:
                        s.delete(old_decision)
                    for stage in prior_stages:
                        if stage.name in ("PURCHASES", "MARKET_PACKET"):
                            s.delete(stage)
                    if saved:
                        saved.id = c.id + ":entry-original"
                        saved.kind = "entry-original"
                    c.data = {
                        "one_time_replacement": archive,
                        "entry_deadline_override": "This replacement only; current Monday market session",
                    }
                    self.bump(s)
                    s.flush()
                if (
                    self.stage_done(s, c, "PURCHASES")
                    or c.status.startswith("SKIPPED")
                    or c.status == "MISSED"
                ):
                    return
                if not self.allowed(s, monday):
                    return
                if (
                    not replace_failed_once
                    and self.settings.market_provider != "synthetic"
                    and now.astimezone(NY)
                    > datetime.fromisoformat(
                        scheduled(monday, cfg.monday_deadline_hour)
                    ).astimezone(NY)
                ):
                    c.status = "MISSED"
                    c.data = {"reason": "Monday entry deadline passed"}
                    self.bump(s)
                    return
                if list(
                    s.scalars(
                        select(Position).where(
                            Position.account_id == cfg.experiment_id,
                            Position.status == "OPEN",
                        )
                    )
                ):
                    raise ValueError("Unresolved prior positions block opening")
                account = s.get(Account, cfg.experiment_id)
                reconcile(s, account)
                eligible, reason = eligible_week(monday)
                if not eligible:
                    c.status = "SKIPPED_NONSTANDARD_WEEK"
                    c.data = {"reason": reason, "pnl": "0.00"}
                    self.bump(s)
                    skipped = True
                else:
                    skipped = False
                    c.status = "RESEARCHING"
            if skipped:
                self.request_publish()
                return
            cutoff = (
                scheduled(monday, 9, 35)
                if cfg.market_provider == "synthetic"
                else iso(now)
            )
            with self.sessions.begin() as s:
                c = self.cycle(s, monday)
                saved = s.get(Snapshot, c.id + ":entry")
                if saved:
                    packet = saved.data
                else:
                    packet = screen(
                        provider(cfg).packet(cfg.universe.split(","), cutoff, "entry"),
                        cfg,
                    )
                    s.add(
                        Snapshot(
                            id=c.id + ":entry", cycle_id=c.id, kind="entry", data=packet
                        )
                    )
                    self.mark(s, c, "MARKET_PACKET")
                cash = str(s.get(Account, cfg.experiment_id).cash)
                cycle_id = c.id
            try:
                # Neither independent researcher receives the other's output.
                def research(role):
                    try:
                        output = self.invoke(
                            role,
                            "RESEARCH",
                            {
                                "cycle_id": cycle_id,
                                "market": packet,
                                "research_universe": cfg.universe.split(","),
                                "independent_web_research": cfg.independent_web_research
                                and cfg.codex_mode == "real",
                            },
                            packet["cutoff"],
                            cycle_id,
                            cycle_id
                            + (":replacement:" if replace_failed_once else ":")
                            + role,
                        )
                        return role, output, None
                    except (RunnerError, ValueError) as exc:
                        return role, None, exc

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(research, ROLES[:2]))
                with self.sessions.begin() as s:
                    c = s.get(Cycle, cycle_id)
                    for role, result, error in results:
                        if result is None:
                            continue
                        output, run_id = result
                        for candidate in output["candidates"]:
                            id = f"{cycle_id}:{role}:{candidate['rank']}"
                            if not s.get(Proposal, id):
                                s.add(
                                    Proposal(
                                        id=id,
                                        cycle_id=cycle_id,
                                        run_id=run_id,
                                        ticker=candidate["ticker"],
                                        data=candidate,
                                    )
                                )
                    s.flush()
                    proposals = [
                        dict(id=p.id, role=s.get(AgentRun, p.run_id).role, **p.data)
                        for p in s.scalars(
                            select(Proposal)
                            .where(Proposal.cycle_id == cycle_id)
                            .order_by(Proposal.id)
                        )
                    ]
                if any(error is not None for role, result, error in results):
                    raise RunnerError("REQUIRED_RESEARCHER_FAILED")
                decision, run_id = self.invoke(
                    "manager",
                    "DECISION",
                    {
                        "cycle_id": cycle_id,
                        "cash": cash,
                        "proposals": proposals,
                        "research_reports": [
                            {"role": r, **result[0]}
                            for r, result, error in results
                            if result
                        ],
                        "market": packet,
                        "limits": {
                            "ticker": cfg.max_stock_allocation,
                            "deployed": cfg.max_deployed,
                        },
                    },
                    packet["cutoff"],
                    cycle_id,
                    cycle_id
                    + (":replacement:manager" if replace_failed_once else ":manager"),
                )
                with self.sessions.begin() as s:
                    c = s.get(Cycle, cycle_id)
                    account = s.get(Account, cfg.experiment_id)
                    if not self.stage_done(s, c, "PURCHASES"):
                        grouped = validate_decision(
                            decision, proposals, account.cash, cfg
                        )
                        ok, reason = eligible_week(monday)
                        if not ok:
                            raise ValueError("Execution calendar changed: " + reason)
                        # Obtain executable observations at order time, separately from frozen research.
                        execution_cutoff = (
                            packet["cutoff"]
                            if cfg.market_provider == "synthetic"
                            else iso(utcnow())
                        )
                        if (
                            cfg.market_provider != "synthetic"
                            and utcnow()
                            > datetime.fromisoformat(
                                scheduled(
                                    monday,
                                    15
                                    if replace_failed_once
                                    else cfg.monday_deadline_hour,
                                    45 if replace_failed_once else 0,
                                )
                            )
                        ):
                            raise ValueError("Monday execution deadline passed")
                        execution = (
                            executable_packet(
                                cfg, list(grouped), "entry", execution_cutoff
                            )
                            if grouped
                            else packet
                        )
                        buy(s, account, c, grouped, execution, cfg)
                        s.add(Decision(cycle_id=cycle_id, run_id=run_id, data=decision))
                        c.status = "OPEN" if grouped else "HOLD_CASH"
                        c.data = dict(
                            c.data,
                            starting_equity=cash,
                            entry_cutoff=packet["cutoff"],
                            risk_checks=[
                                "proposal membership",
                                "combined ticker concentration",
                                "deployment cap",
                                "cash arithmetic",
                                "quote freshness",
                                "calendar",
                                "ledger reconciliation",
                            ],
                        )
                        self.mark(s, c, "PURCHASES")
            except (RunnerError, ValueError) as exc:
                with self.sessions.begin() as s:
                    c = s.get(Cycle, cycle_id)
                    c.status = "HOLD_CASH"
                    c.data = dict(
                        c.data,
                        reason="Required research/decision failed; retained cash",
                        starting_equity=cash,
                        failure_category=exc.category
                        if isinstance(exc, RunnerError)
                        else "RISK_OR_DATA",
                    )
                    self.mark(s, c, "PURCHASES")
                self.incident(
                    "OPEN_FAILURE",
                    "Opening failed validation; account remains cash-funded and unchanged.",
                )
            self.request_publish()

    def close(self, monday, now=None):
        cfg = self.settings
        now = now or utcnow()
        with self.lock():
            with self.sessions.begin() as s:
                c = self.cycle(s, monday)
                if c.status == "COMPLETED" and self.stage_done(s, c, "REVIEW"):
                    return
                if c.status.startswith("SKIPPED") or c.status == "MISSED":
                    return
                if not self.stage_done(s, c, "PURCHASES"):
                    c.status = "MISSED"
                    c.data = {
                        "reason": "Opening trigger or purchases missing",
                        "pnl": "0.00",
                    }
                    self.bump(s)
                    return
                cycle_id = c.id
                liquidated = self.stage_done(s, c, "LIQUIDATION")
                tickers = [
                    p.ticker
                    for p in s.scalars(
                        select(Proposal).where(Proposal.cycle_id == c.id)
                    )
                ]
            cutoff = (
                scheduled(monday + timedelta(days=4), 15, 45)
                if cfg.market_provider == "synthetic"
                else iso(now)
            )
            if not liquidated:
                try:
                    if cfg.market_provider != "synthetic":
                        from app.market_data.providers import parse

                        cal = __import__("exchange_calendars").get_calendar("XNYS")
                        day = now.astimezone(NY).date().isoformat()
                        if (
                            not cal.is_session(day)
                            or not cal.session_open(day).to_pydatetime()
                            <= now
                            <= cal.session_close(day).to_pydatetime()
                        ):
                            raise ValueError(
                                "Recovery requires an open supported exchange session"
                            )
                    packet = executable_packet(cfg, tickers, "exit", cutoff)
                    with self.sessions.begin() as s:
                        c = s.get(Cycle, cycle_id)
                        account = s.get(Account, cfg.experiment_id)
                        sell(s, account, c, packet, cfg)
                        remaining = list(
                            s.scalars(
                                select(Position).where(
                                    Position.cycle_id == cycle_id,
                                    Position.status == "OPEN",
                                )
                            )
                        )
                        if remaining:
                            c.status = "RECOVERY_REQUIRED"
                            self.bump(s)
                        pnl = money(account.cash - Decimal(c.data["starting_equity"]))
                        entry = s.get(Snapshot, cycle_id + ":entry")
                        comparisons = []
                        for p in s.scalars(
                            select(Proposal).where(Proposal.cycle_id == cycle_id)
                        ):
                            start = (
                                entry.data["quotes"].get(p.ticker) if entry else None
                            )
                            end = packet["quotes"].get(p.ticker)
                            if start and end:
                                comparisons.append(
                                    dict(
                                        proposal_id=p.id,
                                        ticker=p.ticker,
                                        expected_return=p.data["expected_return"],
                                        observed_return=float(
                                            Decimal(end["price"])
                                            / Decimal(start["price"])
                                            - 1
                                        ),
                                        label="HYPOTHETICAL matched-window raw-price comparison",
                                    )
                                )
                        benchmark = None
                        if (
                            entry
                            and entry.data["benchmark"]["price"]
                            and packet.get("benchmark", {}).get("price")
                        ):
                            benchmark = str(
                                Decimal(packet.get("benchmark", {}).get("price"))
                                / Decimal(entry.data["benchmark"]["price"])
                                - 1
                            )
                        if remaining:
                            fill_count = s.scalar(
                                select(func.count())
                                .select_from(Fill)
                                .join(Order, Order.id == Fill.order_id)
                                .join(Position, Position.id == Order.position_id)
                                .where(
                                    Position.cycle_id == cycle_id, Order.side == "SELL"
                                )
                            )
                            partial_id = f"{cycle_id}:partial-exit:{fill_count}"
                            if not s.get(Snapshot, partial_id):
                                s.add(
                                    Snapshot(
                                        id=partial_id,
                                        cycle_id=cycle_id,
                                        kind=f"partial-exit:{fill_count}",
                                        data=packet,
                                    )
                                )
                            c.data = dict(
                                c.data,
                                partial_exit_cutoff=cutoff,
                                reason="Partial exit; remaining position requires recovery",
                            )
                        else:
                            s.add(
                                Snapshot(
                                    id=cycle_id + ":exit",
                                    cycle_id=cycle_id,
                                    kind="exit",
                                    data=packet,
                                )
                            )
                            c.data = dict(
                                c.data,
                                pnl=str(pnl),
                                pnl_precise=str(
                                    account.cash - Decimal(c.data["starting_equity"])
                                ),
                                ending_equity=str(money(account.cash)),
                                exit_cutoff=cutoff,
                                comparisons=comparisons,
                                benchmark_return=benchmark,
                                extended_holding=(
                                    now.astimezone(NY).date()
                                    > monday + timedelta(days=4)
                                )
                                if cfg.market_provider != "synthetic"
                                else False,
                            )
                            c.status = "RECONCILED"
                            self.mark(s, c, "LIQUIDATION")
                    if remaining:
                        raise ValueError(
                            "Partial liquidation committed; recovery required"
                        )
                except (ValueError, httpx_error()) as exc:
                    with self.sessions.begin() as s:
                        c = s.get(Cycle, cycle_id)
                        c.status = "RECOVERY_REQUIRED"
                        self.bump(s)
                    self.incident(
                        "EXIT_FAILURE",
                        "Unsupported liquidation observation. Positions remain open; operator recovery required.",
                    )
                    self.request_publish()
                    raise
            with self.sessions() as s:
                c = s.get(Cycle, cycle_id)
                exit_packet = s.get(Snapshot, cycle_id + ":exit").data
                evidence = [q["evidence_id"] for q in exit_packet["quotes"].values()]
                entry = s.get(Snapshot, cycle_id + ":entry")
                evidence += (
                    [q["evidence_id"] for q in entry.data["quotes"].values()]
                    if entry
                    else []
                )
                current = dict(
                    c.data,
                    cycle_id=cycle_id,
                    cutoff=exit_packet["cutoff"],
                    evidence_ids=evidence,
                )
            try:
                output, run_id = self.invoke(
                    "analyst",
                    "REVIEW",
                    current,
                    exit_packet["cutoff"],
                    cycle_id,
                    cycle_id + ":analyst",
                )
                with self.sessions.begin() as s:
                    c = s.get(Cycle, cycle_id)
                    if not self.stage_done(s, c, "REVIEW"):
                        s.add(Review(cycle_id=cycle_id, run_id=run_id, data=output))
                        learning = apply(s, cfg, c, output["patches"], evidence)
                        c.data = dict(
                            c.data,
                            summary=output["summary"],
                            learning_results=learning,
                            review_status="AVAILABLE",
                        )
                        c.status = "COMPLETED"
                        self.mark(s, c, "REVIEW")
            except RunnerError:
                with self.sessions.begin() as s:
                    c = s.get(Cycle, cycle_id)
                    c.status = "COMPLETED"
                    c.data = dict(c.data, review_status="UNAVAILABLE")
                    self.bump(s)
                self.incident(
                    "REVIEW_FAILURE",
                    "Trading results reconciled; analyst review unavailable and independently retryable.",
                )
            self.request_publish()

    def meeting(self, sunday):
        if sunday.weekday() != 6:
            raise ValueError("Meeting date must be Sunday")
        from app.meetings.orchestrator import MeetingOrchestrator

        with self.lock():
            MeetingOrchestrator(self).run(sunday)
        self.request_publish()


def httpx_error():
    import httpx

    return httpx.HTTPError
