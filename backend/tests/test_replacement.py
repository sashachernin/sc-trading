from datetime import date, datetime, timezone
import pytest
from sqlalchemy import select
from app.models import Cycle, Decision, AgentRun, Audit, Snapshot


def test_one_time_replacement_preserves_original_and_rejects_repeat(lab):
    monday = date(2026, 9, 14)
    lab.open(monday)
    with lab.sessions.begin() as s:
        c = lab.cycle(s, monday)
        # Represent the cash-only initial failure; synthetic fixture normally buys.
        from app.models import Position, Order, Fill, Ledger, Account, Proposal

        for model in (Fill, Order, Position, Proposal):
            for row in s.scalars(select(model)):
                s.delete(row)
            s.flush()
        for row in s.scalars(select(Ledger).where(Ledger.cycle_id == c.id)):
            s.delete(row)
        s.get(Account, lab.settings.experiment_id).cash = 1000
        c.status = "HOLD_CASH"
        d = s.get(Decision, c.id)
        d.data = {**d.data, "allocations": []}
        original_id = d.run_id
    lab.open(
        monday,
        now=datetime(2026, 9, 14, 18, tzinfo=timezone.utc),
        replace_failed_once=True,
    )
    with lab.sessions() as s:
        assert s.get(AgentRun, original_id)
        assert s.scalar(select(Audit).where(Audit.action == "replace-failed-open-once"))
        assert s.get(Snapshot, c.id + ":entry-original")
        assert s.get(Decision, c.id).run_id.endswith(":replacement:manager")
        assert s.get(Cycle, c.id).data["one_time_replacement"]
    with pytest.raises(ValueError, match="unreplaced"):
        lab.open(
            monday,
            now=datetime(2026, 9, 14, 18, tzinfo=timezone.utc),
            replace_failed_once=True,
        )
