import pytest
from app.config import Settings
from app.models import Base
from app.services import Lab


@pytest.fixture
def lab(tmp_path):
    cfg = Settings(
        database_url=f"sqlite:///{tmp_path}/lab.db",
        state_dir=tmp_path / "state",
        experiment_id="synthetic-test",
        experiment_start="2026-09-14",
        codex_mode="fake",
        market_provider="synthetic",
        materialize_local_export=False,
        _env_file=None,
    )
    lab = Lab(cfg)
    Base.metadata.create_all(lab.engine)
    lab.initialize()
    return lab
