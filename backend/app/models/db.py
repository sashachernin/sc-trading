from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    String,
    JSON,
    DateTime,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Integer,
    Boolean,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    start: Mapped[str] = mapped_column(String)
    end: Mapped[str] = mapped_column(String)
    synthetic: Mapped[bool] = mapped_column(Boolean)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    revision: Mapped[int] = mapped_column(Integer, default=0)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), primary_key=True)
    cash: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal("1000"))
    __table_args__ = (CheckConstraint("cash >= 0"),)


class Cycle(Base):
    __tablename__ = "weekly_cycles"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    monday: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="PLANNED")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("experiment_id", "monday"),)


class Stage(Base):
    __tablename__ = "stages"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    cycle_id: Mapped[str] = mapped_column(ForeignKey("weekly_cycles.id"))
    name: Mapped[str] = mapped_column(String)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (UniqueConstraint("cycle_id", "name"),)


class Ledger(Base):
    __tablename__ = "cash_ledger"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    cycle_id: Mapped[str | None] = mapped_column(
        ForeignKey("weekly_cycles.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    kind: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    cycle_id: Mapped[str] = mapped_column(ForeignKey("weekly_cycles.id"))
    ticker: Mapped[str] = mapped_column(String)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    basis: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    status: Mapped[str] = mapped_column(String, default="OPEN")
    __table_args__ = (
        CheckConstraint("quantity >= 0"),
        UniqueConstraint("cycle_id", "ticker"),
    )


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    position_id: Mapped[str] = mapped_column(ForeignKey("positions.id"))
    side: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Fill(Base):
    __tablename__ = "fills"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True)
    ticker: Mapped[str] = mapped_column(String)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    fee: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    data: Mapped[dict] = mapped_column(JSON)


class Snapshot(Base):
    __tablename__ = "market_snapshots"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    cycle_id: Mapped[str] = mapped_column(ForeignKey("weekly_cycles.id"))
    kind: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("cycle_id", "kind"),)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    cycle_id: Mapped[str | None] = mapped_column(
        ForeignKey("weekly_cycles.id"), nullable=True
    )
    role: Mapped[str] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    prompt: Mapped[str] = mapped_column(String)
    prompt_hash: Mapped[str] = mapped_column(String)
    manifest: Mapped[dict] = mapped_column(JSON)
    output: Mapped[dict] = mapped_column(JSON)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON)


class Proposal(Base):
    __tablename__ = "proposals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    cycle_id: Mapped[str] = mapped_column(ForeignKey("weekly_cycles.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    ticker: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON)


class Decision(Base):
    __tablename__ = "manager_decisions"
    cycle_id: Mapped[str] = mapped_column(
        ForeignKey("weekly_cycles.id"), primary_key=True
    )
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    data: Mapped[dict] = mapped_column(JSON)


class Review(Base):
    __tablename__ = "reviews"
    cycle_id: Mapped[str] = mapped_column(
        ForeignKey("weekly_cycles.id"), primary_key=True
    )
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    data: Mapped[dict] = mapped_column(JSON)


class Lesson(Base):
    __tablename__ = "memory_items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"))
    cycle_id: Mapped[str] = mapped_column(ForeignKey("weekly_cycles.id"))
    role: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSON)


class Overlay(Base):
    __tablename__ = "overlay_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"))
    role: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer)
    lesson_ids: Mapped[list] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("experiment_id", "role", "version"),)


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"))
    sunday: Mapped[str] = mapped_column(String)
    cycle_id: Mapped[str | None] = mapped_column(
        ForeignKey("weekly_cycles.id"), nullable=True
    )
    upcoming_monday: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    context: Mapped[dict] = mapped_column(JSON)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("experiment_id", "sunday"),)


class Turn(Base):
    __tablename__ = "meeting_turns"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), unique=True)
    data: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("meeting_id", "sequence"),)


class Publication(Base):
    __tablename__ = "publications"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"))
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    data: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("experiment_id", "revision"),)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"))
    kind: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=10)
    status: Mapped[str] = mapped_column(String, default="QUEUED", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)


class Audit(Base):
    __tablename__ = "operator_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"))
    action: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"))
    category: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


def connect(settings):
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def foreign_keys(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")

    return engine, sessionmaker(engine, expire_on_commit=False)


class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    position_id: Mapped[str] = mapped_column(ForeignKey("positions.id"))
    kind: Mapped[str] = mapped_column(String)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal(0))
    data: Mapped[dict] = mapped_column(JSON)


class SettingVersion(Base):
    __tablename__ = "setting_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    key: Mapped[str] = mapped_column(String)
    value: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
