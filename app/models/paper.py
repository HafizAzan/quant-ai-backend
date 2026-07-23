from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class PaperAccount(Base):
    __tablename__ = "paper_accounts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    cash: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    equity: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    starting_equity: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    win_rate_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    max_drawdown_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    learning_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="practice")
    fee_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=10)  # 10 bps = 0.10%
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    orders: Mapped[list["PaperOrder"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    positions: Mapped[list["PaperPosition"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class PaperOrder(Base):
    __tablename__ = "paper_orders"
    __table_args__ = (Index("ix_paper_orders_account_status", "account_id", "status"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # long | short
    order_type: Mapped[str] = mapped_column(String(8), nullable=False)  # market | limit
    size: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    size_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    size_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="fixed")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending|filled|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped[PaperAccount] = relationship(back_populates="orders")
    fills: Mapped[list["PaperFill"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class PaperPosition(Base):
    __tablename__ = "paper_positions"
    __table_args__ = (Index("ix_paper_positions_account_status", "account_id", "status"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    size: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    size_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    entry: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    current: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    health: Mapped[str] = mapped_column(String(16), nullable=False, default="healthy")
    lifecycle: Mapped[str] = mapped_column(String(16), nullable=False, default="opened")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")  # open | closed
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    future_commentary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    chart_snapshot_label: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    risk_changes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    trade_events: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    execution_history: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped[PaperAccount] = relationship(back_populates="positions")
    events: Mapped[list["PaperPositionEvent"]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )


class PaperFill(Base):
    __tablename__ = "paper_fills"
    __table_args__ = (Index("ix_paper_fills_account_created", "account_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    position_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_positions.id", ondelete="SET NULL"),
        nullable=True,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped[PaperOrder] = relationship(back_populates="fills")


class PaperEquityPoint(Base):
    __tablename__ = "paper_equity_points"
    __table_args__ = (Index("ix_paper_equity_account_range", "account_id", "range_key"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    range_key: Mapped[str] = mapped_column(String(8), nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PaperPositionEvent(Base):
    __tablename__ = "paper_position_events"
    __table_args__ = (Index("ix_paper_pos_events_sort", "position_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_positions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    time_label: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    position: Mapped[PaperPosition] = relationship(back_populates="events")


class PaperSentinelSuggestion(Base):
    __tablename__ = "paper_sentinel_suggestions"
    __table_args__ = (UniqueConstraint("account_id", name="uq_paper_sentinel_account"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    suggested_tp: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
