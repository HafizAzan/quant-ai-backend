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


class LiveAccount(Base):
    __tablename__ = "live_accounts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    exchange: Mapped[str] = mapped_column(String(64), nullable=False, default="Binance")
    api_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_trading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trading_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_only_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    margin_type: Mapped[str] = mapped_column(String(16), nullable=False, default="cross")
    total_unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    risk_controls: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    portfolio_exposure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    system_status: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    market_monitor: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    balances: Mapped[list["LiveBalance"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    positions: Mapped[list["LivePosition"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    orders: Mapped[list["LiveOrder"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    activities: Mapped[list["LiveActivityEvent"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    guardian_alerts: Mapped[list["LiveGuardianAlert"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class LiveBalance(Base):
    __tablename__ = "live_balances"
    __table_args__ = (UniqueConstraint("account_id", "asset", name="uq_live_balances_account_asset"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("live_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    asset: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[str] = mapped_column(String(64), nullable=False, default="0")
    change_24h: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    account: Mapped[LiveAccount] = relationship(back_populates="balances")


class LivePosition(Base):
    __tablename__ = "live_positions"
    __table_args__ = (Index("ix_live_positions_account_status", "account_id", "status"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("live_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    size: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    size_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    entry: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    mark: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    margin_type: Mapped[str] = mapped_column(String(16), nullable=False, default="cross")
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    health: Mapped[str] = mapped_column(String(32), nullable=False, default="healthy")
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped[LiveAccount] = relationship(back_populates="positions")


class LiveOrder(Base):
    __tablename__ = "live_orders"
    __table_args__ = (Index("ix_live_orders_account_status", "account_id", "status"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("live_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, default="limit")
    type_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    amount_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    filled_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    margin_type: Mapped[str] = mapped_column(String(16), nullable=False, default="cross")
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped[LiveAccount] = relationship(back_populates="orders")


class LiveActivityEvent(Base):
    __tablename__ = "live_activity_events"
    __table_args__ = (Index("ix_live_activity_account_created", "account_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("live_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    timestamp_label: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    account: Mapped[LiveAccount] = relationship(back_populates="activities")


class LiveGuardianAlert(Base):
    __tablename__ = "live_guardian_alerts"
    __table_args__ = (Index("ix_live_guardian_account_sort", "account_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("live_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    action_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    account: Mapped[LiveAccount] = relationship(back_populates="guardian_alerts")


class LiveEmergencyEvent(Base):
    __tablename__ = "live_emergency_events"
    __table_args__ = (Index("ix_live_emergency_user_created", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
