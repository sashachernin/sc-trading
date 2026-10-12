from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Role = Literal["researcher_a", "researcher_b", "manager", "analyst"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Candidate(Strict):
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.]{0,9}$")
    company: str = Field(min_length=1, max_length=120)
    rank: int = Field(ge=1, le=3)
    max_allocation: Decimal = Field(gt=0, le=Decimal(".4"))
    expected_return: float = Field(ge=-1, le=2)
    downside: float = Field(ge=-1, le=0)
    probability_profit: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    thesis: str = Field(min_length=1, max_length=1200)
    catalysts: list[str] = Field(max_length=5)
    risks: list[str] = Field(min_length=1, max_length=5)
    invalidation: str = Field(max_length=500)
    assumptions: list[str] = Field(max_length=5)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)


class Research(Strict):
    role: Literal["researcher_a", "researcher_b"]
    cutoff: str
    snapshot_id: str
    candidates: list[Candidate] = Field(max_length=3)
    abstention_reason: str | None

    @model_validator(mode="after")
    def abstention(self):
        if not self.candidates and not self.abstention_reason:
            raise ValueError("Explicit abstention required")
        if len({c.ticker for c in self.candidates}) != len(self.candidates):
            raise ValueError("Duplicate candidate")
        if [c.rank for c in self.candidates] != list(
            range(1, len(self.candidates) + 1)
        ):
            raise ValueError("Ranks must be contiguous")
        return self


class Allocation(Strict):
    proposal_id: str
    amount: Decimal = Field(gt=0)
    percent: Decimal = Field(gt=0, le=Decimal(".4"))
    rationale: str = Field(min_length=1, max_length=700)


class Rejection(Strict):
    proposal_id: str
    rationale: str = Field(min_length=1, max_length=700)


class ManagerDecision(Strict):
    reviewed_ids: list[str]
    allocations: list[Allocation] = Field(max_length=6)
    rejections: list[Rejection] = Field(max_length=6)
    retained_cash: Decimal = Field(ge=0)
    hold_cash: bool
    summary: str = Field(max_length=1200)
    risk_considerations: list[str] = Field(max_length=8)
    uncertainty: str = Field(max_length=500)


class Patch(Strict):
    target: Literal["researcher_a", "researcher_b", "manager"]
    operation: Literal["add", "replace", "retire", "hypothesis", "parameter"]
    lesson_id: str | None
    text: str = Field(min_length=1, max_length=700)
    parameter: Literal["minimum_confidence", "catalyst_weight"] | None
    value: float | None
    evidence_ids: list[str] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0, le=1)
    expected_effect: str = Field(max_length=500)
    duration_weeks: int = Field(ge=1, le=12)
    success_metric: str = Field(max_length=300)
    rollback_condition: str = Field(max_length=300)
    expiry: str


class Scorecard(Strict):
    role: Role
    score: float = Field(ge=0, le=1)
    assessment: str = Field(max_length=700)


class AnalystReview(Strict):
    summary: str = Field(max_length=2500)
    scorecards: list[Scorecard] = Field(min_length=3, max_length=3)
    forecast_comparisons: list[str] = Field(max_length=6)
    selected_vs_rejected: str = Field(max_length=1000)
    execution_effects: str = Field(max_length=700)
    error_categories: list[str] = Field(max_length=8)
    successes: list[str] = Field(max_length=6)
    weaknesses: list[str] = Field(max_length=6)
    limitations: str = Field(max_length=700)
    evidence_ids: list[str] = Field(min_length=1, max_length=24)
    patches: list[Patch] = Field(max_length=6)

    @model_validator(mode="after")
    def scorecard_roles(self):
        if {s.role for s in self.scorecards} != {
            "researcher_a",
            "researcher_b",
            "manager",
        }:
            raise ValueError("Review must score both researchers and manager once")
        return self


class Closing(Strict):
    title: str = Field(min_length=1, max_length=120)
    standfirst: str = Field(max_length=500)
    recap: str = Field(max_length=1500)
    takeaways: list[str] = Field(max_length=5)
    focus_areas: list[str] = Field(max_length=5)
    open_questions: list[str] = Field(max_length=3)


class MeetingTurn(Strict):
    meeting_id: str
    sequence: int = Field(ge=1, le=11)
    speaker: Role
    phase: Literal["opening", "updates", "discussion", "wrap-up"]
    message_markdown: str = Field(min_length=1, max_length=1400)
    reply_to_turn_ids: list[str] = Field(max_length=10)
    evidence_ids: list[str] = Field(max_length=12)
    next_speaker: Role | None
    closing: Closing | None

    @model_validator(mode="after")
    def word_limit(self):
        if len(self.message_markdown.split()) > 180:
            raise ValueError("Turn exceeds 180 words")
        if self.sequence == 11 and (self.speaker != "manager" or self.closing is None):
            raise ValueError("Manager closing required")
        if self.sequence != 11 and self.closing is not None:
            raise ValueError("Closing only on turn 11")
        return self


CONTRACTS = {
    "RESEARCH": Research,
    "DECISION": ManagerDecision,
    "REVIEW": AnalystReview,
    "MEETING_TURN": MeetingTurn,
}
