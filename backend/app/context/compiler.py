import hashlib, json, math
from pathlib import Path
from datetime import date
from sqlalchemy import select
from app.config import ROOT
from app.models import Lesson, Overlay, Cycle

ROLES = {
    "researcher_a": "researcher_fundamental",
    "researcher_b": "researcher_momentum",
    "manager": "manager",
    "analyst": "analyst",
}
BUDGETS = {
    "rules": 4000,
    "overlay": 4000,
    "current": 14000,
    "recent": 5000,
    "older": 3000,
    "contract": 2000,
}


def canonical(data):
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def digest(data):
    return hashlib.sha256(canonical(data).encode()).hexdigest()


def estimate(text):
    try:
        import tiktoken

        return len(
            tiktoken.get_encoding("o200k_base").encode(text, disallowed_special=())
        )
    except Exception:
        return len(text.encode("utf-8"))  # conservative fallback, one token per byte


class PromptCompiler:
    def __init__(self, settings):
        self.settings = settings

    def compile(self, session, role, purpose, current, contract, cutoff):
        lessons = session.scalars(
            select(Lesson)
            .where(
                Lesson.experiment_id == self.settings.experiment_id,
                Lesson.role == role,
                Lesson.status == "ACTIVE",
            )
            .order_by(Lesson.version, Lesson.id)
        ).all()
        lessons = [
            l
            for l in lessons
            if l.data["expiry"] >= cutoff[:10] and l.cycle_id != current.get("cycle_id")
        ][-12:]
        overlays = session.scalars(
            select(Overlay)
            .where(
                Overlay.experiment_id == self.settings.experiment_id,
                Overlay.role == role,
            )
            .order_by(Overlay.version.desc())
        ).first()
        weeks = session.scalars(
            select(Cycle)
            .where(
                Cycle.experiment_id == self.settings.experiment_id,
                Cycle.monday < cutoff[:10],
                Cycle.status == "COMPLETED",
            )
            .order_by(Cycle.monday.desc())
        ).all()
        recent = [
            {
                "id": w.id,
                "status": w.status,
                "pnl": w.data.get("pnl"),
                "summary": w.data.get("summary", ""),
            }
            for w in weeks[:8]
        ]
        older = {
            "count": len(weeks[8:]),
            "net_pnl": str(sum(float(w.data.get("pnl", 0)) for w in weeks[8:])),
        }
        rules = (ROOT / "prompts" / ROLES[role] / "v1.md").read_text()
        if purpose == "MEETING_TURN":
            rules += "\n" + (ROOT / "prompts/meeting/v1.md").read_text()
            recent = []
            older = {}
        pinned = current.get("pinned_overlay")
        lesson_data = (
            [dict(id=l.id, **l.data) for l in lessons]
            if pinned is None
            else pinned["lessons"]
        )
        lesson_ids = [x["id"] for x in lesson_data]
        sections = {
            "rules": rules,
            "overlay": "ACTIVE LEARNING OVERLAY\nApply these versioned research lessons alongside the fixed role contract and current evidence. Treat confidence and expiry as part of each lesson.\n"
            + canonical(lesson_data),
            "current": canonical(
                {k: v for k, v in current.items() if k != "pinned_overlay"}
            ),
            "recent": canonical(recent),
            "older": canonical(older),
            "contract": canonical(contract.model_json_schema()),
        }
        budgets = (
            BUDGETS
            if purpose != "MEETING_TURN"
            else {
                "rules": 1000,
                "overlay": 1000,
                "current": 9000,
                "recent": 0,
                "older": 0,
                "contract": 1000,
            }
        )
        reductions = []
        # Required evidence and contracts are never silently truncated.
        for name, text in sections.items():
            if name in ("recent", "older") and estimate(text) > budgets[name]:
                sections[name] = "[]" if name == "recent" else "{}"
                reductions.append(name)
            elif estimate(text) > budgets[name]:
                raise ValueError("Context section exceeds budget: " + name)
        prompt = "\n\n".join(k.upper() + "\n" + v for k, v in sections.items())
        limit = 12000 if purpose == "MEETING_TURN" else 32000
        if estimate(prompt) > limit:
            raise ValueError("Total context budget exceeded")
        manifest = {
            "base_prompt": "v1",
            "overlay_version": (
                pinned["version"]
                if pinned is not None
                else overlays.version
                if overlays
                else 0
            ),
            "lesson_ids": lesson_ids,
            "recent_week_ids": [x["id"] for x in recent],
            "cutoff": cutoff,
            "estimated_tokens": estimate(prompt),
            "estimator": "o200k_base-or-utf8-upper-bound",
            "section_sizes": {k: estimate(v) for k, v in sections.items()},
            "reductions": reductions,
        }
        if len(prompt.encode()) > 256000:
            raise ValueError("Prompt exceeds byte limit")
        # Enforce actual estimated tokens and bytes separately.
        if manifest["estimated_tokens"] > limit:
            raise ValueError("Conservative token estimate exceeds limit")
        if purpose == "MEETING_TURN":
            if estimate(sections["rules"]) + estimate(sections["overlay"]) > 2000:
                raise ValueError("Meeting instruction budget exceeded")
            if estimate(canonical(current.get("transcript", []))) > 4000:
                raise ValueError("Meeting transcript input budget exceeded")
            source = {
                k: v
                for k, v in current.items()
                if k not in ("transcript", "pinned_overlay")
            }
            if estimate(canonical(source)) > 5000:
                raise ValueError("Meeting source input budget exceeded")
        return prompt, manifest
