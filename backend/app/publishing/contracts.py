from typing import Literal
from pydantic import Field
from app.agents.contracts import Strict


class FileEntry(Strict):
    path: str
    sha256: str = Field(pattern="^[0-9a-f]{64}$")
    bytes: int = Field(ge=0, le=4000000)
    schema_version: Literal["1"]


class Manifest(Strict):
    schema_version: Literal["1"]
    snapshot_id: str
    source_revision: int = Field(ge=0)
    experiment_id: str
    label: Literal["PAPER / SIMULATED"]
    synthetic: bool
    created_at: str
    source_cutoff: str
    valuation_time: str
    next_expected_publication: str
    files: list[FileEntry]


class AccountOverview(Strict):
    label: Literal["PAPER / SIMULATED"]
    currency: Literal["USD"]
    initial_cash: str
    equity: str
    cash: str
    invested_value: str
    realized_pnl: str
    unrealized_pnl: str
    cumulative_pnl: str
    cumulative_return: str
    monthly_pnl: str
    rolling_four_week_pnl: str
    target_monthly_profit: Literal["100.00"]
    target_is_experimental: Literal[True]
    completed_cycles: int
    skipped_cycles: int
    valuation_time: str
    equity_series: list[dict]
    positions: list[dict]
    fills: list[dict]
    latest_meeting: str | None
