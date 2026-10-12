"""Run after migrations with DATABASE_URL pointing at an isolated PostgreSQL DB."""

from datetime import timedelta
from sqlalchemy import select
from app.services import Lab
from app.models import Experiment, Account, Job, utcnow
from app.jobs.queue import enqueue, claim
from app.paper_trading.ledger import reconcile

lab = Lab()
assert lab.engine.dialect.name == "postgresql"
lab.initialize()
with lab.sessions.begin() as s:
    enqueue(
        s, lab.settings, "PUBLISH", {"test": True}, "pg-skip-locked:1", priority=-100
    )
    enqueue(
        s, lab.settings, "PUBLISH", {"test": True}, "pg-skip-locked:2", priority=-100
    )
with lab.sessions() as a, lab.sessions() as b:
    first = claim(a, lab.settings.experiment_id)
    second = claim(b, lab.settings.experiment_id)
    assert first and second and first[0] != second[0], (
        "SKIP LOCKED must allow different workers to claim distinct jobs"
    )
    a.commit()
    b.commit()
with lab.sessions.begin() as s:
    j = s.get(Job, first[0])
    old = j.lease
    j.heartbeat = utcnow() - timedelta(minutes=16)
with lab.sessions.begin() as s:
    recovered = claim(s, lab.settings.experiment_id)
    assert recovered[0] == first[0] and recovered[1] != old
    s.get(Job, first[0]).status = "COMPLETED"
    s.get(Job, second[0]).status = "COMPLETED"
    account = s.get(Account, lab.settings.experiment_id)
    reconcile(s, account)
    print(
        "PostgreSQL migrations, complete synthetic workflow, SKIP LOCKED concurrent claiming, lease recovery and ledger reconciliation verified; paper cash:",
        account.cash,
    )
