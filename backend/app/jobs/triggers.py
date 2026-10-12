from datetime import timedelta
from app.models import utcnow, Audit
from app.services import Lab, NY
from app.jobs.queue import enqueue


def trigger(kind):
    lab = Lab()
    lab.initialize()
    today = utcnow().astimezone(NY).date()
    expected = {"OPEN": 0, "CLOSE": 4, "MEETING": 6}[kind]
    if today.weekday() != expected:
        raise ValueError("Trigger invoked on wrong market weekday")
    with lab.sessions.begin() as s:
        payload = (
            {"sunday": str(today)}
            if kind == "MEETING"
            else {"monday": str(today - timedelta(days=today.weekday()))}
        )
        enqueue(
            s,
            lab.settings,
            kind,
            payload,
            f"{kind}:{today}",
            priority=0 if kind == "CLOSE" else 10,
        )
        s.add(
            Audit(
                experiment_id=lab.settings.experiment_id,
                action="CRON_" + kind,
                data={"date": str(today)},
            )
        )
        lab.bump(s)
