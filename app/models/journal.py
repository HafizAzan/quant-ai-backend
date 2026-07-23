from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class JournalProfile(Base):
    """Per-user evolution score + journal desk widgets."""

    __tablename__ = "journal_profiles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    level: Mapped[str] = mapped_column(String(64), nullable=False, default="Beginner Trader")
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discipline: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    psychology: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_management: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    biggest_weakness: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    current_mission: Mapped[str] = mapped_column(Text, nullable=False, default="")
    estimated_improvement: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    analytics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    patterns: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    allocation: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    monthly_progress: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    daily_pnl: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    strategy_insight: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("ix_journal_entries_user_traded", "user_id", "traded_at"),
        Index("ix_journal_entries_user_outcome", "user_id", "outcome"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    paper_position_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    strategy_tag: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    emotion_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, default="1h")
    market_condition: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="breakeven")
    pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    roi_percent: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    risk_reward: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    duration: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    exited_at_label: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    entry_price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    exit_price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    psychology_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    mistakes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    improvement: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    candles: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    entry_time: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    exit_time: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_group: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    timeline: Mapped[list["JournalTimelineEvent"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class JournalTimelineEvent(Base):
    __tablename__ = "journal_timeline_events"
    __table_args__ = (Index("ix_journal_timeline_sort", "entry_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    time_label: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    entry: Mapped[JournalEntry] = relationship(back_populates="timeline")


class JournalCoachItem(Base):
    __tablename__ = "journal_coach_items"
    __table_args__ = (Index("ix_journal_coach_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    action_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
