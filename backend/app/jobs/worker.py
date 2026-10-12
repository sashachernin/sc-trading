import time, threading
from datetime import date, timedelta
from app.services import Lab
from app.models import Job, utcnow, Cycle, Meeting
from app.jobs.queue import claim


def execute_one(lab):
    with lab.sessions.begin() as s:
        claimed = claim(s, lab.settings.experiment_id)
    if not claimed:
        return False
    id, lease = claimed
    lab.active_lease = (id, lease)
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(20):
            with lab.sessions.begin() as s:
                j = s.get(Job, id)
                if j.lease != lease:
                    return
                j.heartbeat = utcnow()

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        with lab.sessions() as s:
            job = s.get(Job, id)
            kind = job.kind
            payload = job.payload
            deadline = (
                job.deadline.replace(tzinfo=__import__("datetime").timezone.utc)
                if job.deadline.tzinfo is None
                else job.deadline
            )
            expired = (
                utcnow() > deadline
                and kind in ("OPEN", "MEETING")
                and lab.settings.market_provider != "synthetic"
            )
        if expired:
            with lab.sessions.begin() as s:
                j = s.get(Job, id)
                if j.lease == lease:
                    j.status = "MISSED"
                    j.error = "DEADLINE_EXPIRED"
                if kind == "OPEN":
                    c = lab.cycle(s, date.fromisoformat(payload["monday"]))
                    c.status = "MISSED"
                    c.data = dict(
                        c.data, reason="Opening job missed deadline", pnl="0.00"
                    )
                    lab.bump(s)
            lab.active_lease = None
            lab.incident(
                "MISSED_" + kind,
                "Scheduled workflow expired before execution; no work was invented.",
            )
            lab.request_publish()
            return True
        if kind == "OPEN":
            lab.open(date.fromisoformat(payload["monday"]))
        elif kind in ("CLOSE", "RECOVERY"):
            lab.close(date.fromisoformat(payload["monday"]))
        elif kind == "MEETING":
            lab.meeting(date.fromisoformat(payload["sunday"]))
        elif kind == "PUBLISH":
            from app.publishing.exporter import export
            from app.publishing.git import deliver

            publication = export(lab)
            if lab.settings.publisher_checkout:
                deliver(lab, publication)
        else:
            raise ValueError("Unknown job type")
        with lab.sessions.begin() as s:
            j = s.get(Job, id)
            if j.lease == lease:
                j.status = "COMPLETED"
                j.heartbeat = utcnow()
    except Exception as exc:
        with lab.sessions.begin() as s:
            j = s.get(Job, id)
            if j.lease == lease:
                j.error = type(exc).__name__
                j.status = "QUEUED" if j.attempts < 3 else "FAILED"
                j.next_attempt = utcnow() + timedelta(seconds=60 * j.attempts)
        lab.active_lease = None
        lab.incident(
            "JOB_FAILURE", f"{kind} job failed; see local CLI status and audit records."
        )
    finally:
        stop.set()
        thread.join(timeout=1)
        lab.active_lease = None
    return True


def main():
    lab = Lab()
    lab.initialize()
    last_scan = 0
    while True:
        from app.operator_settings import effective

        lab.settings = effective(lab.engine, lab.sessions, lab.settings)
        lab.compiler.settings = lab.settings
        lab.runner.settings = lab.settings
        if time.monotonic() - last_scan > 60:
            from app.jobs.recovery import recover_missing

            recover_missing(lab)
            last_scan = time.monotonic()
        if not execute_one(lab):
            time.sleep(3)


if __name__ == "__main__":
    main()
