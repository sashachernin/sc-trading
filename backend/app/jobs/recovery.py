"""Recover absent scheduled deliveries without fabricating completed work."""

from datetime import date, datetime, timedelta
from sqlalchemy import select
from app.models import Experiment, Cycle, Meeting, Position, Job, utcnow
from app.services import NY, scheduled
from app.jobs.queue import enqueue


def recover_missing(lab, now=None):
    if lab.settings.market_provider == "synthetic":
        return
    now = now or utcnow()
    cfg = lab.settings
    local = now.astimezone(NY)
    today = local.date()
    with lab.lock(), lab.sessions.begin() as s:
        e = s.get(Experiment, cfg.experiment_id)
        if not e:
            return
        first = date.fromisoformat(e.start)
        monday = first + timedelta(days=(-first.weekday()) % 7)
        while monday <= today and str(monday) < e.end:
            opening = datetime.fromisoformat(scheduled(monday, 9, 35))
            deadline = datetime.fromisoformat(
                scheduled(monday, cfg.monday_deadline_hour)
            )
            cycle = s.scalar(
                select(Cycle).where(
                    Cycle.experiment_id == e.id, Cycle.monday == str(monday)
                )
            )
            if now >= opening and not cycle and not e.paused:
                if now <= deadline:
                    enqueue(s, cfg, "OPEN", {"monday": str(monday)}, f"OPEN:{monday}")
                else:
                    c = lab.cycle(s, monday)
                    c.status = "MISSED"
                    c.data = {
                        "reason": "No opening invocation committed before entry deadline",
                        "pnl": "0.00",
                    }
                    lab.bump(s)
            if cycle and cycle.status in (
                "OPEN",
                "HOLD_CASH",
                "RECOVERY_REQUIRED",
                "RECONCILED",
            ):
                closing = datetime.fromisoformat(
                    scheduled(monday + timedelta(days=4), 15, 45)
                )
                if now >= closing:
                    if today == monday + timedelta(days=4) and local.hour < 16:
                        enqueue(
                            s,
                            cfg,
                            "CLOSE",
                            {"monday": str(monday)},
                            f"CLOSE:{today}",
                            priority=0,
                        )
                    elif cycle.status in ("OPEN", "RECOVERY_REQUIRED"):
                        # Recovery fills still require supported open-session observations.
                        import exchange_calendars as xcals

                        cal = xcals.get_calendar("XNYS")
                        key = today.isoformat()
                        if (
                            cal.is_session(key)
                            and cal.session_open(key).to_pydatetime()
                            <= now
                            <= cal.session_close(key).to_pydatetime()
                        ):
                            enqueue(
                                s,
                                cfg,
                                "RECOVERY",
                                {"monday": str(monday)},
                                f"RECOVERY:{monday}:{today}",
                                priority=0,
                            )
                        if cycle.status != "RECOVERY_REQUIRED":
                            cycle.status = "RECOVERY_REQUIRED"
                            cycle.data = dict(
                                cycle.data,
                                reason="Missed Friday exit; extended holding requires next supported session",
                            )
                            lab.bump(s)
            sunday = monday + timedelta(days=6)
            if str(sunday) < e.end and today >= sunday and not e.paused:
                start = datetime.fromisoformat(scheduled(sunday, 12))
                end = datetime.fromisoformat(
                    scheduled(sunday, cfg.sunday_deadline_hour)
                )
                meeting = s.scalar(
                    select(Meeting).where(
                        Meeting.experiment_id == e.id, Meeting.sunday == str(sunday)
                    )
                )
                if not meeting and now >= start:
                    if now <= end:
                        enqueue(
                            s,
                            cfg,
                            "MEETING",
                            {"sunday": str(sunday)},
                            f"MEETING:{sunday}",
                        )
                    else:
                        s.add(
                            Meeting(
                                id=f"{e.id}-meeting-{sunday}",
                                experiment_id=e.id,
                                sunday=str(sunday),
                                cycle_id=cycle.id if cycle else None,
                                upcoming_monday=str(sunday + timedelta(days=1)),
                                status="MISSED",
                                context={
                                    "cutoff": scheduled(sunday, 12),
                                    "source": {"status": "MISSED"},
                                    "evidence_ids": [],
                                },
                                data={
                                    "reason": "Sunday delivery window expired; no dialogue invented"
                                },
                            )
                        )
                        lab.bump(s)
            monday += timedelta(weeks=1)
