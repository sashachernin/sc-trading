from datetime import timedelta
from sqlalchemy import select
from app.models import (
    Meeting,
    Turn,
    Cycle,
    Review,
    Account,
    Lesson,
    AgentRun,
    Overlay,
    Proposal,
    Decision,
    Fill,
    Order,
    Position,
    Incident,
)
from app.codex_runner.runner import RunnerError
from app.services import scheduled

NAMES = {
    "researcher_a": {"name": "Avery", "role": "Fundamentals & catalysts"},
    "researcher_b": {"name": "Morgan", "role": "Momentum & price"},
    "manager": {"name": "Casey", "role": "Portfolio manager"},
    "analyst": {"name": "Riley", "role": "Research analyst"},
}


class MeetingOrchestrator:
    def __init__(self, lab):
        self.lab = lab

    def run(self, sunday):
        lab = self.lab
        cfg = lab.settings
        id = f"{cfg.experiment_id}-meeting-{sunday}"
        monday = sunday - timedelta(days=6)
        if cfg.market_provider != "synthetic":
            from app.models import utcnow

            now = utcnow()
            if (
                now.date() != sunday
                or now
                < __import__("datetime").datetime.fromisoformat(scheduled(sunday, 12))
                or now
                > __import__("datetime").datetime.fromisoformat(
                    scheduled(sunday, cfg.sunday_deadline_hour)
                )
            ):
                raise ValueError("Sunday meeting window expired or not yet open")
        with lab.sessions.begin() as s:
            m = s.get(Meeting, id)
            if m and m.status in ("CONTENT_READY", "CONTENT_READY_PARTIAL"):
                return
            if not lab.allowed(s, sunday):
                return
            if not m:
                cycle = s.scalar(
                    select(Cycle).where(
                        Cycle.experiment_id == cfg.experiment_id,
                        Cycle.monday == str(monday),
                    )
                )
                previous = s.scalars(
                    select(Meeting)
                    .where(
                        Meeting.experiment_id == cfg.experiment_id,
                        Meeting.sunday < str(sunday),
                        Meeting.status.in_(["CONTENT_READY", "CONTENT_READY_PARTIAL"]),
                    )
                    .order_by(Meeting.sunday.desc())
                ).first()
                source = {
                    "status": cycle.status if cycle else "KICKOFF",
                    "pnl": cycle.data.get("pnl", "0.00") if cycle else "0.00",
                    "week_id": cycle.id if cycle else None,
                    "cash": str(s.get(Account, cfg.experiment_id).cash),
                    "summary": cycle.data.get("summary", "Review unavailable")
                    if cycle
                    else "First meeting; no completed cycle",
                    "reason": cycle.data.get("reason") if cycle else None,
                }
                review = s.get(Review, cycle.id) if cycle else None
                evidence = review.data["evidence_ids"] if review else []
                if cycle:
                    decision = s.get(Decision, cycle.id)
                    selected = (
                        {x["proposal_id"] for x in decision.data["allocations"]}
                        if decision
                        else set()
                    )
                    source["proposals"] = [
                        {
                            "id": p.id,
                            "role": s.get(AgentRun, p.run_id).role,
                            "ticker": p.ticker,
                            "thesis": p.data["thesis"][:300],
                            "expected_return": p.data["expected_return"],
                            "evidence_ids": p.data["evidence_ids"],
                            "selected": p.id in selected,
                        }
                        for p in s.scalars(
                            select(Proposal).where(Proposal.cycle_id == cycle.id)
                        )
                    ]
                    source["decision"] = (
                        {
                            "summary": decision.data["summary"],
                            "retained_cash": decision.data["retained_cash"],
                            "allocations": decision.data["allocations"],
                        }
                        if decision
                        else None
                    )
                    source["outcomes"] = cycle.data.get("comparisons", [])
                    source["fills"] = [
                        {
                            "id": f.id,
                            "ticker": f.ticker,
                            "quantity": str(f.quantity),
                            "price": str(f.price),
                            "side": s.get(Order, f.order_id).side,
                        }
                        for f in s.scalars(
                            select(Fill)
                            .join(Order, Order.id == Fill.order_id)
                            .join(Position, Position.id == Order.position_id)
                            .where(Position.cycle_id == cycle.id)
                        )
                    ]
                source["incidents"] = [
                    {"category": i.category, "summary": i.summary}
                    for i in s.scalars(
                        select(Incident)
                        .where(Incident.experiment_id == cfg.experiment_id)
                        .order_by(Incident.created_at.desc())
                        .limit(3)
                    )
                ]
                from app.market_data.providers import eligible_week

                ok, reason = eligible_week(sunday + timedelta(days=1))
                source["upcoming_calendar"] = {
                    "monday": str(sunday + timedelta(days=1)),
                    "full_week_eligible": ok,
                    "reason": reason,
                    "news_events": "Unavailable; no upcoming news inferred",
                }
                frozen = {
                    "cutoff": scheduled(sunday, 12),
                    "source": source,
                    "evidence_ids": evidence,
                    "previous_recap": previous.data.get("recap", "")[:1500]
                    if previous
                    else "",
                    "overlay_ids": {
                        r: [
                            l.id
                            for l in s.scalars(
                                select(Lesson).where(
                                    Lesson.experiment_id == cfg.experiment_id,
                                    Lesson.role == r,
                                    Lesson.status == "ACTIVE",
                                )
                            )
                        ]
                        for r in NAMES
                    },
                }
                frozen["overlays"] = {}
                for role in NAMES:
                    ov = s.scalars(
                        select(Overlay)
                        .where(
                            Overlay.experiment_id == cfg.experiment_id,
                            Overlay.role == role,
                        )
                        .order_by(Overlay.version.desc())
                    ).first()
                    frozen["overlays"][role] = {
                        "version": ov.version if ov else 0,
                        "lessons": [
                            dict(id=l.id, **l.data)
                            for l in s.scalars(
                                select(Lesson).where(
                                    Lesson.experiment_id == cfg.experiment_id,
                                    Lesson.role == role,
                                    Lesson.status == "ACTIVE",
                                )
                            )
                            if l.data["expiry"] >= str(sunday)
                        ][:12],
                    }
                m = Meeting(
                    id=id,
                    experiment_id=cfg.experiment_id,
                    sunday=str(sunday),
                    cycle_id=cycle.id if cycle else None,
                    upcoming_monday=str(sunday + timedelta(days=1)),
                    status="RUNNING",
                    context=frozen,
                    data={"unavailable": []},
                )
                s.add(m)
                lab.bump(s)
        invited = []
        unavailable = []
        for sequence in range(1, 12):
            if cfg.market_provider != "synthetic":
                from app.models import utcnow

                if utcnow() > __import__("datetime").datetime.fromisoformat(
                    scheduled(sunday, cfg.sunday_deadline_hour)
                ):
                    raise ValueError("Sunday meeting deadline reached; draft preserved")
            with lab.sessions() as s:
                m = s.get(Meeting, id)
                turns = s.scalars(
                    select(Turn).where(Turn.meeting_id == id).order_by(Turn.sequence)
                ).all()
                existing = next((t for t in turns if t.sequence == sequence), None)
                if existing:
                    if sequence in (6, 8, 10):
                        invited.append(existing.data["speaker"])
                    continue
                unavailable = m.data.get("unavailable", [])
                if sequence in (1, 5, 7, 9, 11):
                    role = "manager"
                elif sequence in (2, 3, 4):
                    role = ["researcher_a", "researcher_b", "analyst"][sequence - 2]
                else:
                    prior = next((t for t in turns if t.sequence == sequence - 1), None)
                    if not prior:
                        raise ValueError("Missing chair routing turn")
                    role = prior.data["next_speaker"]
                    if role in invited:
                        raise ValueError("Duplicate follow-up recipient")
                if role is None or role in unavailable:
                    continue
                phase = (
                    "opening"
                    if sequence == 1
                    else "updates"
                    if sequence <= 4
                    else "wrap-up"
                    if sequence == 11
                    else "discussion"
                )
                remaining = [
                    r
                    for r in ("researcher_a", "researcher_b", "analyst")
                    if r not in invited and r not in unavailable
                ]
                # Preserve the latest complete turns and all references supplied to this run.
                transcript = [dict(id=t.id, **t.data) for t in turns][-4:]
                current = {
                    "meeting_id": id,
                    "sequence": sequence,
                    "phase": phase,
                    "source": m.context["source"],
                    "transcript": transcript,
                    "remaining": remaining,
                    "evidence_ids": m.context["evidence_ids"],
                    "previous_recap": m.context["previous_recap"],
                    "pinned_overlay": m.context.get("overlays", {}).get(
                        role, {"version": 0, "lessons": []}
                    ),
                }
                cutoff = m.context["cutoff"]
                cycle_id = m.cycle_id
                meeting_runs = list(
                    s.scalars(select(AgentRun).where(AgentRun.id.like(id + ":run:%")))
                )
                used = sum(
                    max(0, len(r.metadata_.get("attempts", [])) - 1)
                    for r in meeting_runs
                )
                max_attempts = 1 + max(0, 2 - used)
            try:
                out, run_id = lab.invoke(
                    role,
                    "MEETING_TURN",
                    current,
                    cutoff,
                    cycle_id,
                    f"{id}:run:{sequence}",
                    max_attempts=max_attempts,
                )
            except RunnerError:
                with lab.sessions.begin() as s:
                    m = s.get(Meeting, id)
                    if role == "manager":
                        m.status = "FAILED"
                        lab.bump(s)
                        raise
                    unavailable = list(set(m.data.get("unavailable", []) + [role]))
                    m.data = dict(m.data, unavailable=unavailable)
                    lab.bump(s)
                continue
            with lab.sessions.begin() as s:
                m = s.get(Meeting, id)
                if not s.get(Turn, f"{id}:turn:{sequence}"):
                    s.add(
                        Turn(
                            id=f"{id}:turn:{sequence}",
                            meeting_id=id,
                            sequence=sequence,
                            run_id=run_id,
                            data=out,
                        )
                    )
                    lab.bump(s)
                    if sequence == 11:
                        count = len(
                            list(s.scalars(select(Turn).where(Turn.meeting_id == id)))
                        )
                        m.status = (
                            "CONTENT_READY_PARTIAL"
                            if unavailable or count < 11
                            else "CONTENT_READY"
                        )
                        m.data = dict(
                            m.data,
                            **out["closing"],
                            participants=NAMES,
                            turn_count=count,
                            generated_at=__import__("app.models", fromlist=["utcnow"])
                            .utcnow()
                            .isoformat(),
                            label="AI-generated team discussion / PAPER / SIMULATED research",
                            synthetic=cfg.market_provider == "synthetic",
                        )
            if sequence in (6, 8, 10):
                invited.append(role)
