import argparse, json, subprocess
from datetime import date, timedelta
from sqlalchemy import select
from app.config import Settings
from app.models import *
from app.services import Lab, NY
from app.jobs.queue import enqueue
from app.jobs.worker import execute_one


def main():
    p = argparse.ArgumentParser(
        description="AI Investment Lab — PAPER / SIMULATED only"
    )
    p.add_argument(
        "command",
        choices=[
            "init",
            "preflight",
            "status",
            "demo",
            "run-open-cycle",
            "run-close-cycle",
            "run-sunday-meeting",
            "worker-once",
            "publish-site",
            "pause",
            "resume",
            "retry",
            "recover-exit",
            "approve-lesson",
            "rollback-lesson",
            "set-setting",
        ],
    )
    p.add_argument("--date", type=date.fromisoformat)
    p.add_argument("--weeks", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--id")
    p.add_argument("--key")
    p.add_argument("--value")
    p.add_argument("--yes", action="store_true")
    args = p.parse_args()
    cfg = Settings()
    lab = Lab(cfg)
    cfg = lab.settings
    if args.command == "preflight":
        report = {
            "python": __import__("sys").version.split()[0],
            "database_dialect": lab.engine.dialect.name,
            "market_provider": cfg.market_provider,
            "codex_mode": cfg.codex_mode,
            "visibility": cfg.site_visibility,
            "private_access_verified": cfg.private_access_verified,
            "models": {
                r: cfg.model_for(r) or "UNCONFIGURED"
                for r in ("researcher_a", "researcher_b", "manager", "analyst")
            },
        }
        if cfg.codex_mode == "real":
            report["codex_version"] = subprocess.check_output(
                [cfg.codex_binary, "--version"], text=True, timeout=10
            ).strip()
        print(json.dumps(report, indent=2))
        return
    lab.initialize()
    today = args.date or utcnow().astimezone(NY).date()
    monday = today - timedelta(days=today.weekday())
    if args.command == "init":
        print("Initialized PAPER / SIMULATED account: $1,000.00")
        return
    if args.command == "status":
        with lab.sessions() as s:
            e = s.get(Experiment, cfg.experiment_id)
            a = s.get(Account, e.id)
            report = {
                "label": "PAPER / SIMULATED",
                "experiment": e.id,
                "paused": e.paused,
                "cash": str(a.cash),
                "revision": e.revision,
                "cycles": [
                    {"id": c.id, "status": c.status}
                    for c in s.scalars(select(Cycle).where(Cycle.experiment_id == e.id))
                ],
                "jobs": [
                    {
                        "id": j.id,
                        "status": j.status,
                        "attempts": j.attempts,
                        "error": j.error,
                    }
                    for j in s.scalars(select(Job).where(Job.experiment_id == e.id))
                ],
            }
        print(json.dumps(report, indent=2))
        return
    if args.command == "demo":
        if cfg.market_provider != "synthetic" or cfg.codex_mode != "fake":
            raise ValueError("Demo requires a synthetic experiment and fake Codex")
        if not 1 <= args.weeks <= 52:
            raise ValueError("Weeks must be 1–52")
        monday = args.date or cfg.experiment_start
        monday += timedelta(days=(-monday.weekday()) % 7)
        for i in range(args.weeks):
            day = monday + timedelta(weeks=i)
            lab.open(day)
            lab.close(day)
            lab.meeting(day + timedelta(days=6))
        from app.publishing.exporter import export

        publication = export(lab)
        print("Synthetic experiment exported:", publication.id)
        return
    if args.command == "worker-once":
        execute_one(lab)
        return
    if args.command == "publish-site":
        from app.publishing.exporter import export

        publication = export(lab)
        print("Snapshot validated:", publication.id)
        if not args.dry_run:
            from app.publishing.git import deliver

            deliver(lab, publication)
        return
    consequential = args.command in (
        "resume",
        "recover-exit",
        "approve-lesson",
        "rollback-lesson",
        "set-setting",
    )
    if consequential and not args.yes:
        raise ValueError("Use --yes to confirm this audited operator action")
    with lab.sessions.begin() as s:
        s.add(
            Audit(
                experiment_id=cfg.experiment_id,
                action=args.command,
                data={
                    "date": str(today),
                    "id": args.id,
                    "key": args.key,
                    "value": args.value if args.key else None,
                },
            )
        )
        lab.bump(s)
        if args.command == "set-setting":
            from app.operator_settings import update_setting

            if not args.key or args.value is None:
                raise ValueError("--key and --value are required")
            update_setting(s, lab, args.key, args.value)
            return
        if args.command in ("pause", "resume"):
            s.get(Experiment, cfg.experiment_id).paused = args.command == "pause"
            return
        if args.command in ("approve-lesson", "rollback-lesson"):
            from app.learning.gate import overlay

            lesson = s.get(Lesson, args.id)
            if not lesson or lesson.experiment_id != cfg.experiment_id:
                raise ValueError("Unknown lesson")
            if args.command == "approve-lesson":
                if cfg.learning_mode == "shadow_then_promote":
                    raise ValueError(
                        "Shadow promotion unavailable until independently measured evaluation is implemented"
                    )
                if lesson.data.get("validation_errors") or lesson.data["expiry"] < str(
                    today
                ):
                    raise ValueError("Invalid/expired lesson")
                active = list(
                    s.scalars(
                        select(Lesson).where(
                            Lesson.experiment_id == cfg.experiment_id,
                            Lesson.role == lesson.role,
                            Lesson.status == "ACTIVE",
                        )
                    )
                )
                newly = list(
                    s.scalars(
                        select(Lesson).where(
                            Lesson.cycle_id == lesson.cycle_id,
                            Lesson.status == "ACTIVE",
                        )
                    )
                )
                if len(active) >= 12 or len(newly) >= 3:
                    raise ValueError("Activation cap exceeded")
                if lesson.data["operation"] not in ("hypothesis", "add", "parameter"):
                    raise ValueError("Use auto_bounded for validated replace/retire")
                lesson.status = "ACTIVE"
            else:
                lesson.status = "ROLLED_BACK"
            s.flush()
            overlay(s, cfg, lesson.role)
            return
        if args.command == "retry":
            j = s.get(Job, args.id)
            if not j or j.experiment_id != cfg.experiment_id or j.status == "RUNNING":
                raise ValueError("Invalid retry job")
            j.status = "QUEUED"
            j.next_attempt = utcnow()
            j.attempts = 0
            return
        kind = {
            "run-open-cycle": "OPEN",
            "run-close-cycle": "CLOSE",
            "run-sunday-meeting": "MEETING",
            "recover-exit": "RECOVERY",
        }[args.command]
        payload = (
            {"sunday": str(today)} if kind == "MEETING" else {"monday": str(monday)}
        )
        enqueue(
            s,
            cfg,
            kind,
            payload,
            f"{kind}:{today}",
            priority=0 if kind in ("CLOSE", "RECOVERY") else 10,
        )
    print("Queued", kind, "— run the worker to execute")


if __name__ == "__main__":
    main()
