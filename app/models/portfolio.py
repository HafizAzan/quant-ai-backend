from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
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


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    total_balance: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    realized_pnl_ytd: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    equity: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    change_24h_percent: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    mtd_percent: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    daily_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    weekly_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    weekly_target_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    ai_confidence_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    ai_confidence_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    win_rate_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    win_rate_period: Mapped[str] = mapped_column(String(64), nullable=False, default="Last 30 Days")
    win_streak: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    profit_factor: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    balance_spark: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    ai_score_overall: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_score_risk: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    ai_score_diversification: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    ai_score_liquidity: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    ai_score_volatility: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    ai_score_capital_allocation: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    ai_score_recommendation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    holdings: Mapped[list["Holding"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", name="uq_holdings_portfolio_symbol"),
        Index("ix_holdings_portfolio_symbol", "portfolio_id", "symbol"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    allocation: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    avg_entry: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ai_analysis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_assessment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suggested_actions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    trade_history: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")


class OpenPosition(Base):
    __tablename__ = "open_positions"
    __table_args__ = (Index("ix_open_positions_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    asset: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    leverage: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    size: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    entry: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    mark: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    pnl: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    pnl_percent: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PerformancePoint(Base):
    __tablename__ = "performance_points"
    __table_args__ = (
        Index("ix_perf_user_range_series_time", "user_id", "range_key", "series_kind", "time"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    range_key: Mapped[str] = mapped_column(String(8), nullable=False)
    series_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)


class AllocationSlice(Base):
    __tablename__ = "allocation_slices"
    __table_args__ = (Index("ix_allocation_user_view", "user_id", "view"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    view: Mapped[str] = mapped_column(String(32), nullable=False)
    slice_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#5b8def")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MonthlyReturn(Base):
    __tablename__ = "monthly_returns"
    __table_args__ = (UniqueConstraint("user_id", "period_key", name="uq_monthly_returns_user_period"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    period_key: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PortfolioHealthMetric(Base):
    __tablename__ = "portfolio_health_metrics"
    __table_args__ = (Index("ix_health_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(String(64), nullable=False)
    tone: Mapped[str] = mapped_column(String(16), nullable=False, default="default")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AiRecommendation(Base):
    __tablename__ = "ai_recommendations"
    __table_args__ = (Index("ix_ai_rec_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PortfolioTimelineEvent(Base):
    __tablename__ = "portfolio_timeline_events"
    __table_args__ = (Index("ix_timeline_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    time_label: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
        Index("ix_watchlist_user_sort", "user_id", "sort_order"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    change_percent: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (Index("ix_activity_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    time_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TradingSignal(Base):
    __tablename__ = "trading_signals"
    __table_args__ = (Index("ix_signals_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    pair: Mapped[str] = mapped_column(String(64), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    entry: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    target: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    position: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AiAnalysisSummary(Base):
    __tablename__ = "ai_analysis_summaries"
    __table_args__ = (Index("ix_ai_analysis_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
