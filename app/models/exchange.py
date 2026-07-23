from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class ExchangeAccount(Base):
    """Exchange API credentials (encrypted at rest) + sync metadata."""

    __tablename__ = "exchange_accounts"
    __table_args__ = (UniqueConstraint("user_id", "exchange", "label", name="uq_exchange_accounts_user_ex_label"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    exchange: Mapped[str] = mapped_column(String(64), nullable=False, default="binance")
    label: Mapped[str] = mapped_column(String(120), nullable=False, default="Primary")
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    permissions: Mapped[str] = mapped_column(String(32), nullable=False, default="trade")  # read|trade
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_testnet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="never")
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    balances_cache: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
