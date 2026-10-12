from datetime import date, timedelta
from sqlalchemy import select
from app.models import Lesson, Overlay

TARGETS = ("researcher_a", "researcher_b", "manager")


def overlay(session, settings, role):
    last = session.scalars(
        select(Overlay)
        .where(Overlay.experiment_id == settings.experiment_id, Overlay.role == role)
        .order_by(Overlay.version.desc())
    ).first()
    version = last.version + 1 if last else 1
    ids = list(
        session.scalars(
            select(Lesson.id)
            .where(
                Lesson.experiment_id == settings.experiment_id,
                Lesson.role == role,
                Lesson.status == "ACTIVE",
            )
            .order_by(Lesson.id)
        )
    )
    session.add(
        Overlay(
            id=f"{settings.experiment_id}:{role}:{version}",
            experiment_id=settings.experiment_id,
            role=role,
            version=version,
            lesson_ids=ids,
        )
    )


def apply(session, settings, cycle, patches, evidence_ids):
    activated = len(
        list(
            session.scalars(
                select(Lesson).where(
                    Lesson.cycle_id == cycle.id,
                    Lesson.status.in_(["ACTIVE", "RETIRED", "ROLLED_BACK"]),
                )
            )
        )
    )
    results = []
    for i, patch in enumerate(patches):
        id = f"{cycle.id}:patch:{i}"
        existing = session.get(Lesson, id)
        if existing:
            results.append({"id": id, "status": existing.status})
            continue
        errors = []
        target = patch["target"]
        expiry = date.fromisoformat(patch["expiry"])
        week = date.fromisoformat(cycle.monday)
        if not set(patch["evidence_ids"]) <= set(evidence_ids):
            errors.append("unknown evidence")
        if not week < expiry <= week + timedelta(weeks=12):
            errors.append("invalid expiry")
        if patch["operation"] == "parameter" and (
            patch["value"] is None
            or not 0 <= patch["value"] <= 1
            or patch["parameter"] is None
        ):
            errors.append("parameter out of bounds")
        prior = session.get(Lesson, patch["lesson_id"]) if patch["lesson_id"] else None
        if patch["operation"] in ("replace", "retire") and (
            not prior
            or prior.role != target
            or prior.experiment_id != settings.experiment_id
        ):
            errors.append("invalid prior lesson")
        active = session.scalars(
            select(Lesson).where(
                Lesson.experiment_id == settings.experiment_id,
                Lesson.role == target,
                Lesson.status == "ACTIVE",
            )
        ).all()
        for l in active:
            if l.data["expiry"] < cycle.monday:
                l.status = "EXPIRED"
        count = sum(l.status == "ACTIVE" for l in active)
        if count >= 12 and patch["operation"] not in ("retire", "replace"):
            errors.append("memory cap")
        status = "REJECTED" if errors else "CANDIDATE"
        if not errors and settings.learning_mode == "auto_bounded" and activated < 3:
            status = "ACTIVE"
            activated += 1
        # Soft parameters are bounded research guidance in the same versioned overlay.
        last = session.scalars(
            select(Overlay)
            .where(
                Overlay.experiment_id == settings.experiment_id, Overlay.role == target
            )
            .order_by(Overlay.version.desc())
        ).first()
        lesson = Lesson(
            id=id,
            experiment_id=settings.experiment_id,
            cycle_id=cycle.id,
            role=target,
            status=status,
            version=last.version + 1 if last else 1,
            data=dict(patch, validation_errors=errors, mode=settings.learning_mode),
        )
        session.add(lesson)
        if status == "ACTIVE":
            if prior:
                prior.status = "RETIRED"
            if patch["operation"] == "retire":
                lesson.status = "RETIRED"
            session.flush()
            overlay(session, settings, target)
        results.append({"id": id, "status": lesson.status, "errors": errors})
    return results
