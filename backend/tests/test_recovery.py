from datetime import date, datetime, timezone
from sqlalchemy import select
from app.jobs.recovery import recover_missing
from app.models import Cycle, Meeting, Job


def test_missed_delivery_records_no_fabricated_work(lab):
    lab.settings.market_provider = (
        "alpaca"  # Recovery/calendar logic needs no provider credentials.
    )
    recover_missing(lab, datetime(2026, 9, 21, 12, tzinfo=timezone.utc))
    with lab.sessions() as s:
        c = s.scalar(select(Cycle))
        assert c.monday == "2026-09-14"
        assert c.status == "MISSED"
        m = s.scalar(select(Meeting))
        assert m.status == "MISSED"
        assert m.data["reason"].startswith("Sunday delivery")
    recover_missing(lab, datetime(2026, 9, 21, 12, tzinfo=timezone.utc))
    with lab.sessions() as s:
        assert len(list(s.scalars(select(Cycle)))) == 1
        assert len(list(s.scalars(select(Meeting)))) == 1


def test_missed_cron_within_window_enqueues(lab):
    lab.settings.market_provider = "alpaca"
    recover_missing(lab, datetime(2026, 9, 14, 13, 40, tzinfo=timezone.utc))
    with lab.sessions() as s:
        jobs = list(s.scalars(select(Job)))
        assert len(jobs) == 1
        assert jobs[0].kind == "OPEN"
        assert jobs[0].payload["monday"] == "2026-09-14"


def test_stale_worker_fenced_before_commit(lab):
    from app.jobs.queue import enqueue, claim
    import pytest

    with lab.sessions.begin() as s:
        enqueue(s, lab.settings, "OPEN", {"monday": "2026-09-14"}, "fence")
    with lab.sessions.begin() as s:
        old = claim(s, lab.settings.experiment_id)
    lab.active_lease = old
    with lab.sessions.begin() as s:
        s.get(Job, old[0]).lease = "replacement-worker"
    with pytest.raises(ValueError, match="Stale worker"):
        with lab.sessions.begin() as s:
            lab.bump(s)
    lab.active_lease = None
