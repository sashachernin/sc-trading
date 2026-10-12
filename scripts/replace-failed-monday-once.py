"""One-time user-authorized replacement of the 2026-10-12 cash-only opening."""

from datetime import date
from app.config import Settings
from app.services import Lab

cfg = Settings()
if (
    cfg.experiment_id != "paper-2026-10-12"
    or cfg.codex_mode != "real"
    or not cfg.independent_web_research
):
    raise SystemExit(
        "This replacement is restricted to the original forward experiment and real browsing"
    )
lab = Lab(cfg)
lab.open(date(2026, 10, 12), replace_failed_once=True)
from app.publishing.exporter import export

publication = export(lab)
print("Replacement completed; validated snapshot:", publication.id)
