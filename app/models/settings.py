from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class UserSettings(Base):
    """Per-user security, AI, and risk preferences (one row per user)."""

    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_settings_user_id"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # security
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    two_factor_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_timeout: Mapped[str] = mapped_column(String(8), nullable=False, default="30")  # 15|30|60|240
    # ai
    primary_engine: Mapped[str] = mapped_column(String(64), nullable=False, default="gpt-4o-finance")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.45)
    autonomous_execution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # risk
    max_drawdown_daily: Mapped[str] = mapped_column(String(32), nullable=False, default="2.5")
    max_position_size: Mapped[str] = mapped_column(String(32), nullable=False, default="5000")
    max_leverage: Mapped[str] = mapped_column(String(32), nullable=False, default="10")
    critical_stop_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    critical_stop_drawdown_pct: Mapped[str] = mapped_column(String(32), nullable=False, default="15")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserApiKey(Base):
    """Platform API keys (QuantAI), not exchange credentials."""

    __tablename__ = "user_api_keys"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    permission: Mapped[str] = mapped_column(String(32), nullable=False, default="read-only")  # read-write|read-only
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
