from sqlalchemy import select, inspect
from app.config import Settings
from app.models import SettingVersion

ALLOWED = {
    "codex_model_researcher_a",
    "codex_model_researcher_b",
    "codex_model_manager",
    "codex_model_analyst",
    "codex_reasoning",
    "independent_web_research",
    "research_timeout",
    "learning_mode",
    "max_stock_allocation",
    "max_deployed",
    "spread_bps",
    "slippage_bps",
    "fee_usd",
    "quote_max_age_seconds",
    "monday_deadline_hour",
    "sunday_deadline_hour",
}


def effective(engine, session_factory, settings):
    if not inspect(engine).has_table("setting_versions"):
        return settings
    with session_factory() as s:
        versions = s.scalars(
            select(SettingVersion)
            .where(SettingVersion.experiment_id == settings.experiment_id)
            .order_by(SettingVersion.id)
        ).all()
        values = settings.model_dump()
        for row in versions:
            values[row.key] = row.value["value"]
        return Settings(**values, _env_file=None)


def update_setting(session, lab, key, value):
    if key not in ALLOWED:
        raise ValueError("Setting is not operator-allowlisted")
    proposed = Settings(
        **dict(lab.settings.model_dump(), **{key: value}), _env_file=None
    )
    session.add(
        SettingVersion(
            experiment_id=lab.settings.experiment_id,
            key=key,
            value={"value": getattr(proposed, key)},
        )
    )
    lab.bump(session)
