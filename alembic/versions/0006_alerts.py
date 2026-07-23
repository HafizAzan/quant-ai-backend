"""Alerts tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_alerts"
down_revision: Union[str, None] = "0005_analysis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False),
        sa.Column("channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("entry", sa.Numeric(24, 8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(24, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(24, 8), nullable=True),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count_24h", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_alerts_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(op.f("ix_alerts_user_id"), "alerts", ["user_id"], unique=False)
    op.create_index(op.f("ix_alerts_symbol"), "alerts", ["symbol"], unique=False)
    op.create_index(op.f("ix_alerts_category"), "alerts", ["category"], unique=False)
    op.create_index("ix_alerts_user_status_cat", "alerts", ["user_id", "status", "category"], unique=False)
    op.create_index("ix_alerts_user_enabled", "alerts", ["user_id", "enabled"], unique=False)

    op.create_table(
        "alert_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("condition_type", sa.String(length=32), nullable=False),
        sa.Column("operator", sa.String(length=16), nullable=False),
        sa.Column("target_value", sa.Numeric(24, 8), nullable=False),
        sa.Column("logic", sa.String(length=8), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["alert_id"], ["alerts.id"], name=op.f("fk_alert_conditions_alert_id_alerts"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_conditions")),
    )
    op.create_index(op.f("ix_alert_conditions_alert_id"), "alert_conditions", ["alert_id"], unique=False)
    op.create_index("ix_alert_conditions_alert", "alert_conditions", ["alert_id", "sort_order"], unique=False)

    op.create_table(
        "alert_triggers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("badge", sa.String(length=32), nullable=False),
        sa.Column("badge_tone", sa.String(length=16), nullable=False),
        sa.Column("detail", sa.String(length=512), nullable=False),
        sa.Column("mark_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("delivered", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["alert_id"], ["alerts.id"], name=op.f("fk_alert_triggers_alert_id_alerts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_alert_triggers_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_triggers")),
    )
    op.create_index(op.f("ix_alert_triggers_alert_id"), "alert_triggers", ["alert_id"], unique=False)
    op.create_index(op.f("ix_alert_triggers_user_id"), "alert_triggers", ["user_id"], unique=False)
    op.create_index("ix_alert_triggers_user_created", "alert_triggers", ["user_id", "created_at"], unique=False)

    op.create_table(
        "alert_timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("time_label", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_alert_timeline_events_alert_id_alerts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_timeline_events")),
    )
    op.create_index(op.f("ix_alert_timeline_events_alert_id"), "alert_timeline_events", ["alert_id"], unique=False)
    op.create_index("ix_alert_timeline_sort", "alert_timeline_events", ["alert_id", "sort_order"], unique=False)

    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success_rate", sa.String(length=16), nullable=False),
        sa.Column("latency", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_notification_channels_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_channels")),
        sa.UniqueConstraint("user_id", "kind", name="uq_notification_channels_user_kind"),
    )
    op.create_index(op.f("ix_notification_channels_user_id"), "notification_channels", ["user_id"], unique=False)

    op.create_table(
        "alert_watch_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=120), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("tone", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_alert_watch_items_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_watch_items")),
    )
    op.create_index(op.f("ix_alert_watch_items_user_id"), "alert_watch_items", ["user_id"], unique=False)
    op.create_index("ix_alert_watch_user_sort", "alert_watch_items", ["user_id", "sort_order"], unique=False)


def downgrade() -> None:
    op.drop_table("alert_watch_items")
    op.drop_table("notification_channels")
    op.drop_table("alert_timeline_events")
    op.drop_table("alert_triggers")
    op.drop_table("alert_conditions")
    op.drop_table("alerts")
