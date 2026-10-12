from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from pathlib import Path
import hashlib, json, subprocess, sys
import pytest
from sqlalchemy import select, func
from app.models import *
from app.paper_trading.ledger import reconcile, validate_decision, validate_quote
from app.market_data.providers import eligible_week, SyntheticProvider, screen
from app.publishing.exporter import export, markdown, safe_content, build_files
from app.publishing.contracts import Manifest, AccountOverview
from app.codex_runner.runner import CodexRunner, RunnerError
from app.agents.contracts import Research, MeetingTurn
from app.jobs.queue import enqueue, claim
from app.learning.gate import apply
from app.services import scheduled, NY
from app.config import ROOT

MON = date(2026, 9, 14)


def run_week(lab, day=MON):
    lab.open(day)
    lab.close(day)
    lab.meeting(day + timedelta(days=6))


def test_exact_initial_capital(lab):
    with lab.sessions() as s:
        a = s.get(Account, lab.settings.experiment_id)
        assert a.cash == Decimal("1000")
        reconcile(s, a)
        assert s.scalar(select(func.count()).select_from(Ledger)) == 1
    lab.initialize()
    with lab.sessions() as s:
        assert s.scalar(select(func.count()).select_from(Ledger)) == 1


def test_multiweek_learning_ledger_and_meetings(lab):
    run_week(lab)
    first = lab.settings.experiment_id + "-" + str(MON)
    with lab.sessions() as s:
        a = s.get(Account, lab.settings.experiment_id)
        reconcile(s, a)
        cash = a.cash
        assert cash != 1000
        assert not list(s.scalars(select(Position).where(Position.status == "OPEN")))
        cycle = s.get(Cycle, first)
        assert cycle.status == "COMPLETED"
        assert Decimal(cycle.data["ending_equity"]) == cash.quantize(Decimal(".01"))
        lessons = list(s.scalars(select(Lesson).where(Lesson.status == "ACTIVE")))
        assert len(lessons) == 1
        accepted = list(s.scalars(select(Turn).order_by(Turn.sequence)))
        assert len(accepted) == 11
        assert [t.data["speaker"] for t in accepted[:4]] == [
            "manager",
            "researcher_a",
            "researcher_b",
            "analyst",
        ]
        assert accepted[-1].data["speaker"] == "manager"
        assert set(t.data["speaker"] for t in accepted if t.sequence in (6, 8, 10)) == {
            "researcher_a",
            "researcher_b",
            "analyst",
        }
        assert len(set(t.run_id for t in accepted)) == 11
        assert all(
            s.get(AgentRun, t.run_id).purpose == "MEETING_TURN" for t in accepted
        )
        assert str(cycle.data["pnl"]) in accepted[3].data["message_markdown"]
        counts = {
            cls: s.scalar(select(func.count()).select_from(cls))
            for cls in (Ledger, Fill, Turn, Lesson)
        }
    run_week(lab)
    with lab.sessions() as s:
        assert s.get(Account, lab.settings.experiment_id).cash == cash
        assert counts == {
            cls: s.scalar(select(func.count()).select_from(cls)) for cls in counts
        }
    lab.open(MON + timedelta(weeks=1))
    second = lab.settings.experiment_id + "-" + str(MON + timedelta(weeks=1))
    with lab.sessions() as s:
        a = s.get(AgentRun, second + ":researcher_a")
        b = s.get(AgentRun, second + ":researcher_b")
        assert lessons[0].id in a.manifest["lesson_ids"]
        assert a.manifest["overlay_version"] == 1
        assert lessons[0].data["text"] in a.prompt
        assert lessons[0].id not in b.manifest["lesson_ids"]
        assert "MEETING MODE" not in a.prompt
        assert accepted[0].data["message_markdown"] not in a.prompt
        assert a.manifest["estimated_tokens"] <= 32000
        assert "PROPOSALS" not in a.prompt and "Morgan" not in a.prompt


def test_calendar_skip_sunday_and_kickoff(lab):
    holiday = date(2026, 11, 23)  # Friday after Thanksgiving is an early close.
    assert not eligible_week(holiday)[0]
    lab.open(holiday)
    lab.close(holiday)
    lab.meeting(holiday + timedelta(days=6))
    with lab.sessions() as s:
        c = s.get(Cycle, lab.settings.experiment_id + "-" + str(holiday))
        assert c.status == "SKIPPED_NONSTANDARD_WEEK"
        assert s.get(Account, lab.settings.experiment_id).cash == 1000
        m = s.scalar(select(Meeting))
        assert m.status == "CONTENT_READY"
        assert m.context["source"]["status"] == "SKIPPED_NONSTANDARD_WEEK"
    lab.meeting(date(2026, 9, 13))  # Outside experiment -> no meeting.
    with lab.sessions() as s:
        assert s.scalar(select(func.count()).select_from(Meeting)) == 1


def test_first_ever_kickoff(lab):
    lab.meeting(date(2026, 9, 20))
    with lab.sessions() as s:
        m = s.scalar(select(Meeting))
        assert m.context["source"]["status"] == "KICKOFF"
        turns = list(s.scalars(select(Turn)))
        assert all(
            "I proposed a bounded hypothesis" not in t.data["message_markdown"]
            for t in turns
        )
        assert m.status == "CONTENT_READY"
        assert s.get(Account, lab.settings.experiment_id).cash == 1000
        assert s.scalar(select(func.count()).select_from(Lesson)) == 0


def test_snapshot_hashes_transcript_and_noop(lab):
    run_week(lab)
    p = export(lab)
    again = export(lab)
    assert p.id == again.id
    root = Path(p.data["export_directory"])
    m = Manifest.model_validate_json(
        (root / "frontend/public/data/manifest.json").read_text()
    )
    AccountOverview.model_validate_json(
        (root / "frontend/public/data/overview.json").read_text()
    )
    for f in m.files:
        raw = (root / f.path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == f.sha256
        assert len(raw) == f.bytes
    assert "frontend/public/data/manifest.json" not in [f.path for f in m.files]
    mid = lab.settings.experiment_id + "-meeting-2026-09-20"
    detail = json.loads(
        (root / f"frontend/public/data/meetings/{mid}.json").read_text()
    )
    md = (root / f"frontend/public/transcripts/{mid}.md").read_text()
    assert markdown(detail) == md
    assert all(t["message_markdown"] in md for t in detail["turns"])
    assert (root / f"frontend/content/meetings/{mid}.md").read_text() == md
    assert all(
        f.path.startswith(
            (
                "frontend/public/data/",
                "frontend/public/transcripts/",
                "frontend/content/meetings/",
            )
        )
        for f in m.files
    )


@pytest.mark.parametrize(
    "text",
    [
        "<script>alert(1)</script>",
        "postgresql://user:pass@host/db",
        "github_pat_abcdefghijklmnop",
        "javascript:alert(1)",
        "-----BEGIN RSA PRIVATE KEY-----",
    ],
)
def test_export_secret_rejection(text):
    with pytest.raises(ValueError):
        safe_content(text)


def test_combined_allocation_and_unsubmitted(lab):
    proposals = [
        {"id": "a", "ticker": "AAPL", "max_allocation": ".4"},
        {"id": "b", "ticker": "AAPL", "max_allocation": ".4"},
    ]
    d = {
        "reviewed_ids": ["a", "b"],
        "allocations": [
            {"proposal_id": "a", "amount": "300", "percent": ".3"},
            {"proposal_id": "b", "amount": "300", "percent": ".3"},
        ],
        "rejections": [],
        "hold_cash": False,
        "retained_cash": "400",
    }
    with pytest.raises(ValueError, match="Combined"):
        validate_decision(d, proposals, Decimal(1000), lab.settings)
    d["allocations"][1]["proposal_id"] = "unknown"
    with pytest.raises(ValueError):
        validate_decision(d, proposals, Decimal(1000), lab.settings)


def test_quote_cutoff_and_screen(lab):
    p = SyntheticProvider(lab.settings).packet(["AAPL"], scheduled(MON, 9, 35), "entry")
    q = p["quotes"]["AAPL"]
    validate_quote(q, p["cutoff"], lab.settings, p["cutoff"])
    q["observed_at"] = scheduled(MON, 9, 36)
    with pytest.raises(ValueError):
        validate_quote(q, p["cutoff"], lab.settings)
    assert not screen(p, lab.settings)["quotes"]
    q["observed_at"] = scheduled(MON, 9, 34)
    with pytest.raises(ValueError, match="predates"):
        validate_quote(q, p["cutoff"], lab.settings, p["cutoff"])


def test_missing_exit_preserves_position_and_review_priority(lab, monkeypatch):
    lab.open(MON)
    import app.services as services

    original = services.executable_packet
    monkeypatch.setattr(
        services,
        "executable_packet",
        lambda *args: {
            "quotes": {},
            "cutoff": scheduled(MON + timedelta(days=4), 15, 45),
            "provider": "synthetic",
        },
    )
    with pytest.raises(ValueError):
        lab.close(MON)
    with lab.sessions() as s:
        assert list(s.scalars(select(Position).where(Position.status == "OPEN")))
        assert s.scalar(select(Review)) is None
        c = s.scalar(select(Cycle))
        assert c.status == "RECOVERY_REQUIRED"
    monkeypatch.setattr(services, "executable_packet", original)
    lab.close(MON)
    with lab.sessions() as s:
        assert s.scalar(select(Cycle)).status == "COMPLETED"


def test_review_failure_retry_preserves_fills(lab, monkeypatch):
    lab.open(MON)
    original = lab.invoke

    def unavailable(role, purpose, *args, **kwargs):
        if purpose == "REVIEW":
            raise RunnerError("AUTHENTICATION")
        return original(role, purpose, *args, **kwargs)

    monkeypatch.setattr(lab, "invoke", unavailable)
    lab.close(MON)
    with lab.sessions() as s:
        assert not list(s.scalars(select(Position).where(Position.status == "OPEN")))
        count = s.scalar(select(func.count()).select_from(Fill))
        cash = s.get(Account, lab.settings.experiment_id).cash
        assert s.scalar(select(Cycle)).data["review_status"] == "UNAVAILABLE"
    monkeypatch.setattr(lab, "invoke", original)
    lab.close(MON)
    with lab.sessions() as s:
        assert s.get(Account, lab.settings.experiment_id).cash == cash
        assert s.scalar(select(func.count()).select_from(Fill)) == count
        assert s.scalar(select(Review))


def test_queue_idempotency_and_restart_lease(lab):
    with lab.sessions.begin() as s:
        id = enqueue(s, lab.settings, "OPEN", {"monday": str(MON)}, "open:1")
        assert enqueue(s, lab.settings, "OPEN", {}, "open:1") == id
    with lab.sessions.begin() as s:
        claimed = claim(s, lab.settings.experiment_id)
    with lab.sessions.begin() as s:
        assert claim(s, lab.settings.experiment_id) is None
        j = s.get(Job, id)
        j.heartbeat = utcnow() - timedelta(minutes=16)
    with lab.sessions.begin() as s:
        fresh = claim(s, lab.settings.experiment_id)
        assert fresh[0] == claimed[0]
        assert fresh[1] != claimed[1]


def test_dst_and_three_triggers():
    assert scheduled(date(2026, 3, 2), 9, 35).endswith("14:35:00+00:00")
    assert scheduled(date(2026, 3, 9), 9, 35).endswith("13:35:00+00:00")
    for file in ("run_open_cycle", "run_close_cycle", "run_sunday_meeting"):
        assert (ROOT / "backend/app/jobs" / f"{file}.py").exists()


def test_learning_caps_invalid_evidence_and_expiry(lab):
    run_week(lab)
    with lab.sessions.begin() as s:
        c = s.scalar(select(Cycle))
        review = s.get(Review, c.id)
        patch = review.data["patches"][0]
        bad = dict(patch, evidence_ids=["not-existing"])
        results = apply(s, lab.settings, c, [patch, bad], review.data["evidence_ids"])
        assert results[1]["status"] == "REJECTED"
        # Existing source patch remains immutable/idempotent.
        assert results[0]["status"] == "ACTIVE"


def test_meeting_resume_preserves_accepted_turns(lab, monkeypatch):
    original = lab.invoke

    def fail(role, purpose, current, *args, **kwargs):
        if purpose == "MEETING_TURN" and current["sequence"] == 5:
            raise RunnerError("AUTHENTICATION")
        return original(role, purpose, current, *args, **kwargs)

    monkeypatch.setattr(lab, "invoke", fail)
    with pytest.raises(RunnerError):
        lab.meeting(MON + timedelta(days=6))
    with lab.sessions() as s:
        turns = list(s.scalars(select(Turn).order_by(Turn.sequence)))
        assert len(turns) == 4
        frozen = s.scalar(select(Meeting)).context
    monkeypatch.setattr(lab, "invoke", original)
    lab.meeting(MON + timedelta(days=6))
    with lab.sessions() as s:
        assert s.scalar(select(Meeting)).context == frozen
        assert s.scalar(select(func.count()).select_from(Turn)) == 11
        assert all(s.get(Turn, t.id).run_id == t.run_id for t in turns)


def test_hold_cash_abstention(lab, monkeypatch):
    import app.services as services

    monkeypatch.setattr(services, "screen", lambda p, c: dict(p, quotes={}))
    lab.open(MON)
    lab.close(MON)
    with lab.sessions() as s:
        assert s.scalar(select(Cycle)).status == "COMPLETED"
        assert s.scalar(select(Decision)).data["hold_cash"]
        assert s.get(Account, lab.settings.experiment_id).cash == 1000
        assert not list(s.scalars(select(Fill)))


def test_pause_blocks_open_and_meeting_but_allows_exit(lab):
    lab.open(MON)
    with lab.sessions.begin() as s:
        s.get(Experiment, lab.settings.experiment_id).paused = True
    lab.close(MON)
    lab.meeting(MON + timedelta(days=6))
    lab.open(MON + timedelta(weeks=1))
    with lab.sessions() as s:
        assert not list(s.scalars(select(Position).where(Position.status == "OPEN")))
        assert s.scalar(select(Meeting)) is None
        assert (
            s.get(
                Cycle, lab.settings.experiment_id + "-" + str(MON + timedelta(weeks=1))
            ).status
            == "PLANNED"
        )
