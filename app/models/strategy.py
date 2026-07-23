from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = (
        Index("ix_strategies_user_updated", "user_id", "updated_at"),
        Index("ix_strategies_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, default="BTC/USDT")
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, default="15m")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    markets: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    timeframes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="v0.1.0")
    ai_confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_risk: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    estimated_monthly_return: Mapped[str] = mapped_column(String(32), nullable=False, default="—")
    win_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    profit_factor: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    drawdown: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False, default="Binance")
    strategy_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Momentum")
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    author: Mapped[str] = mapped_column(String(120), nullable=False, default="QuantAI Lab")
    last_backtest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_backtest_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    nodes: Mapped[list["StrategyNode"]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan"
    )
    edges: Mapped[list["StrategyEdge"]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan"
    )
    backtests: Mapped[list["BacktestRun"]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan"
    )


class StrategyNode(Base):
    __tablename__ = "strategy_nodes"
    __table_args__ = (Index("ix_strategy_nodes_strategy_sort", "strategy_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    node_key: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    type_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    collapsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation: Mapped[str] = mapped_column(String(16), nullable=False, default="idle")
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ports: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    strategy: Mapped[Strategy] = relationship(back_populates="nodes")


class StrategyEdge(Base):
    __tablename__ = "strategy_edges"
    __table_args__ = (Index("ix_strategy_edges_strategy", "strategy_id"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    edge_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    target_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_port: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_port: Mapped[str | None] = mapped_column(String(32), nullable=True)
    label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    highlighted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    errored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    strategy: Mapped[Strategy] = relationship(back_populates="edges")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (Index("ix_backtest_runs_strategy_created", "strategy_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, default="15m")
    range_label: Mapped[str] = mapped_column(String(32), nullable=False, default="90d")
    win_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    profit_factor: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    drawdown: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    sharpe: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_return: Mapped[str] = mapped_column(String(32), nullable=False, default="—")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    strategy: Mapped[Strategy] = relationship(back_populates="backtests")
