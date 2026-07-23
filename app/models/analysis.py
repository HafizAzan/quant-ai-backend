from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class AiAnalysis(Base):
    """Full chart workspace AI trade thesis (saved or draft)."""

    __tablename__ = "ai_analyses"
    __table_args__ = (
        Index("ix_ai_analyses_user_symbol_tf", "user_id", "symbol", "timeframe"),
        Index("ix_ai_analyses_user_saved", "user_id", "is_saved", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False, default="Binance")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="PRO MODEL")
    lookback: Mapped[int] = mapped_column(Integer, nullable=False, default=200)

    # Quote snapshot at generation time
    open_price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    high_price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    low_price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    close_price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    change_percent: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    volume_label: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    ai_zones_label: Mapped[str] = mapped_column(String(120), nullable=False, default="Supply / Demand Active")

    # Signal panel
    trend: Mapped[str] = mapped_column(String(32), nullable=False, default="NEUTRAL")
    structure: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    structure_note: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    resistance_label: Mapped[str] = mapped_column(String(120), nullable=False, default="Resistance (Supply)")
    resistance_range: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    resistance_strength: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    support_label: Mapped[str] = mapped_column(String(120), nullable=False, default="Support (Demand)")
    support_range: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    support_strength: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_reward_ratio: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    risk_reward_probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reasoning_title: Mapped[str] = mapped_column(String(120), nullable=False, default="AI REASONING")
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Trade plan
    entry: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)

    overlays: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_saved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
