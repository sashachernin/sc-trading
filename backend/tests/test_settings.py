import pytest
from sqlalchemy import select
from app.models import SettingVersion
from app.operator_settings import effective, update_setting


def test_versioned_safe_settings(lab):
    with lab.sessions.begin() as s:
        update_setting(s, lab, "max_stock_allocation", ".25")
    cfg = effective(lab.engine, lab.sessions, lab.settings)
    assert cfg.max_stock_allocation == ".25"
    with lab.sessions() as s:
        assert s.scalar(select(SettingVersion)).key == "max_stock_allocation"
    with lab.sessions.begin() as s:
        with pytest.raises(ValueError):
            update_setting(s, lab, "database_url", "secret")
        with pytest.raises(ValueError):
            update_setting(s, lab, "max_stock_allocation", ".9")
