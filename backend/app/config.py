from pathlib import Path
from datetime import date
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "sqlite:///state/lab.db"
    experiment_id: str = Field(
        default="synthetic-demo", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$"
    )
    experiment_start: date = date(2026, 9, 14)
    market_provider: Literal["synthetic", "alpaca", "yahoo"] = "synthetic"
    codex_mode: Literal["fake", "real"] = "fake"
    codex_binary: str = "codex"
    codex_model_researcher_a: str = ""
    codex_model_researcher_b: str = ""
    codex_model_manager: str = ""
    codex_model_analyst: str = ""
    codex_reasoning: str = "medium"
    codex_auth_home: str = "/var/lib/ai-investment-lab/codex-auth"
    state_dir: Path = ROOT / "state"
    learning_mode: Literal["auto_bounded", "manual", "shadow_then_promote"] = (
        "auto_bounded"
    )
    site_visibility: Literal["private", "public"] = "private"
    private_access_verified: bool = False
    materialize_local_export: bool = True
    publisher_checkout: str = ""
    publish_branch: str = Field(
        default="main", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_/-]{0,100}$"
    )
    deployment_url: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_feed: str = "iex"
    alpaca_asset_base_url: str = "https://paper-api.alpaca.markets"
    universe: str = "AAPL,MSFT,NVDA,AMZN,GOOGL,META"
    quote_max_age_seconds: int = Field(default=120, ge=1, le=900)
    execution_wait_seconds: int = Field(default=90, ge=1, le=180)
    runner_timeout: int = Field(default=180, ge=1, le=600)
    max_output_bytes: int = Field(default=131072, ge=1024, le=1048576)
    max_stock_allocation: str = "0.40"
    max_deployed: str = "0.95"
    spread_bps: str = "2"
    slippage_bps: str = "3"
    fee_usd: str = "0.00"
    monday_deadline_hour: int = 11
    sunday_deadline_hour: int = 16

    @model_validator(mode="after")
    def separate_modes(self):
        if self.market_provider != "synthetic" and self.codex_mode != "real":
            raise ValueError(
                "Real-data experiments require real Codex; fake speech is synthetic only"
            )
        if self.market_provider != "synthetic" and self.experiment_id.startswith(
            "synthetic"
        ):
            raise ValueError("Use a distinct experiment ID for real data")
        from decimal import Decimal

        if not 0 < Decimal(self.max_stock_allocation) <= Decimal(
            ".4"
        ) or not 0 < Decimal(self.max_deployed) <= Decimal(".95"):
            raise ValueError("Risk limits exceed fixed experiment contract")
        if any(
            Decimal(x) < 0 for x in (self.spread_bps, self.slippage_bps, self.fee_usd)
        ):
            raise ValueError("Execution costs cannot be negative")
        return self

    def model_for(self, role):
        return getattr(self, "codex_model_" + role)
