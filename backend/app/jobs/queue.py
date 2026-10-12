from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
import uuid
from sqlalchemy import select, or_
from app.models import Job, utcnow


def enqueue(session, settings, kind, payload, key, priority=10):
    id = settings.experiment_id + ":" + key
    if session.get(Job, id):
        return id
    deadline = utcnow() + timedelta(hours=24)
    if kind in ("OPEN", "MEETING"):
        day = payload.get("monday") or payload.get("sunday")
        if settings.market_provider != "synthetic":
            deadline = datetime.fromisoformat(day).replace(
                hour=settings.monday_deadline_hour
                if kind == "OPEN"
                else settings.sunday_deadline_hour,
                tzinfo=ZoneInfo("America/New_York"),
            )
    session.add(
        Job(
            id=id,
            experiment_id=settings.experiment_id,
            kind=kind,
            payload=payload,
            priority=priority,
            status="QUEUED",
            attempts=0,
            next_attempt=utcnow(),
            deadline=deadline,
        )
    )
    return id


def claim(session, experiment_id):
    now = utcnow()
    stale = now - timedelta(minutes=15)
    # Locks and lease compare-and-set fence abandoned workers.
    job = session.scalars(
        select(Job)
        .where(
            Job.experiment_id == experiment_id,
            or_(
                (Job.status == "QUEUED") & (Job.next_attempt <= now),
                (Job.status == "RUNNING") & (Job.heartbeat < stale),
            ),
        )
        .order_by(Job.priority, Job.next_attempt)
        .with_for_update(skip_locked=True)
        .limit(1)
    ).first()
    if not job:
        return None
    job.status = "RUNNING"
    job.attempts += 1
    job.lease = str(uuid.uuid4())
    job.heartbeat = now
    return job.id, job.lease
