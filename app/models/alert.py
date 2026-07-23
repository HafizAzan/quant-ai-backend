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


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_user_status_cat", "user_id", "status", "category"),
        Index("ix_alerts_user_enabled", "user_id", "enabled"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="price", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="recurring")
    channels: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active|muted|snoozed|archived
    entry: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_analysis_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trigger_count_24h: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    conditions: Mapped[list["AlertCondition"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )
    timeline: Mapped[list["AlertTimelineEvent"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )
    triggers: Mapped[list["AlertTrigger"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )


class AlertCondition(Base):
    __tablename__ = "alert_conditions"
    __table_args__ = (Index("ix_alert_conditions_alert", "alert_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    condition_type: Mapped[str] = mapped_column(String(32), nullable=False, default="price")
    operator: Mapped[str] = mapped_column(String(16), nullable=False, default="above")  # above|below|cross
    target_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    logic: Mapped[str] = mapped_column(String(8), nullable=False, default="and")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    alert: Mapped[Alert] = relationship(back_populates="conditions")


class AlertTrigger(Base):
    __tablename__ = "alert_triggers"
    __table_args__ = (Index("ix_alert_triggers_user_created", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    badge: Mapped[str] = mapped_column(String(32), nullable=False, default="TRIGGERED")
    badge_tone: Mapped[str] = mapped_column(String(16), nullable=False, default="warning")
    detail: Mapped[str] = mapped_column(String(512), nullable=False)
    mark_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    alert: Mapped[Alert] = relationship(back_populates="triggers")


class AlertTimelineEvent(Base):
    __tablename__ = "alert_timeline_events"
    __table_args__ = (Index("ix_alert_timeline_sort", "alert_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    time_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    alert: Mapped[Alert] = relationship(back_populates="timeline")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    __table_args__ = (UniqueConstraint("user_id", "kind", name="uq_notification_channels_user_kind"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="connected")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    success_rate: Mapped[str] = mapped_column(String(16), nullable=False, default="100%")
    latency: Mapped[str] = mapped_column(String(16), nullable=False, default="—")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AlertWatchItem(Base):
    __tablename__ = "alert_watch_items"
    __table_args__ = (Index("ix_alert_watch_user_sort", "user_id", "sort_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tone: Mapped[str] = mapped_column(String(16), nullable=False, default="default")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
