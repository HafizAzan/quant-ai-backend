from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    trading_pair: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="crypto", index=True, nullable=False)
    rank: Mapped[int] = mapped_column(nullable=False, default=0, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    change_24h: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    volume_24h: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False, default=0)
    market_cap: Mapped[Decimal] = mapped_column(Numeric(28, 2), nullable=False, default=0)
    ai_signal: Mapped[str] = mapped_column(String(32), default="Neutral", nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#5B8DEF", nullable=False)
    is_high_volume: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_new_listing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_crypto_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    candles: Mapped[list["Candle"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    favorites: Mapped[list["UserFavorite"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("trading_pair", "timeframe", "open_time", name="uq_candles_pair_tf_time"),
        Index("ix_candles_pair_tf_time", "trading_pair", "timeframe", "open_time"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    trading_pair: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open_time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asset: Mapped[Asset] = relationship(back_populates="candles")


class UserFavorite(Base):
    __tablename__ = "user_favorites"
    __table_args__ = (UniqueConstraint("user_id", "asset_id", name="uq_user_favorites_user_asset"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    asset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asset: Mapped[Asset] = relationship(back_populates="favorites")


class MarketSnapshot(Base):
    """Singleton-style row for fear/greed + dominance (id fixed)."""

    __tablename__ = "market_snapshots"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    fear_greed_score: Mapped[int] = mapped_column(nullable=False, default=50)
    fear_greed_zone: Mapped[str] = mapped_column(String(32), nullable=False, default="Neutral")
    fear_greed_description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    btc_dominance: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    alts_dominance: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    stables_dominance: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    ai_pick_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_pick_confidence: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
