"""Live trading desk tables (simulated exchange MVP)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_live"
down_revision: Union[str, None] = "0009_strategies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "live_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("api_active", sa.Boolean(), nullable=False),
        sa.Column("auto_trading", sa.Boolean(), nullable=False),
        sa.Column("trading_locked", sa.Boolean(), nullable=False),
        sa.Column("risk_only_mode", sa.Boolean(), nullable=False),
        sa.Column("default_leverage", sa.Integer(), nullable=False),
        sa.Column("margin_type", sa.String(length=16), nullable=False),
        sa.Column("total_unrealized_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("risk_controls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("portfolio_exposure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("system_status", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("market_monitor", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_live_accounts_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_accounts")),
        sa.UniqueConstraint("user_id", name=op.f("uq_live_accounts_user_id")),
    )
    op.create_index(op.f("ix_live_accounts_user_id"), "live_accounts", ["user_id"], unique=True)

    op.create_table(
        "live_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.String(length=64), nullable=False),
        sa.Column("change_24h", sa.Numeric(8, 4), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["live_accounts.id"],
            name=op.f("fk_live_balances_account_id_live_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_balances")),
        sa.UniqueConstraint("account_id", "asset", name="uq_live_balances_account_asset"),
    )
    op.create_index(op.f("ix_live_balances_account_id"), "live_balances", ["account_id"], unique=False)

    op.create_table(
        "live_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("size", sa.Numeric(24, 8), nullable=False),
        sa.Column("size_label", sa.String(length=64), nullable=False),
        sa.Column("entry", sa.Numeric(24, 8), nullable=False),
        sa.Column("mark", sa.Numeric(24, 8), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=False),
        sa.Column("margin_type", sa.String(length=16), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("health", sa.String(length=32), nullable=False),
        sa.Column("stop_loss", sa.Numeric(24, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(24, 8), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["live_accounts.id"],
            name=op.f("fk_live_positions_account_id_live_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_positions")),
    )
    op.create_index(op.f("ix_live_positions_account_id"), "live_positions", ["account_id"], unique=False)
    op.create_index("ix_live_positions_account_status", "live_positions", ["account_id", "status"], unique=False)

    op.create_table(
        "live_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("order_type", sa.String(length=16), nullable=False),
        sa.Column("type_label", sa.String(length=64), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=False),
        sa.Column("amount", sa.Numeric(24, 8), nullable=False),
        sa.Column("amount_label", sa.String(length=64), nullable=False),
        sa.Column("filled_percent", sa.Numeric(8, 2), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=False),
        sa.Column("margin_type", sa.String(length=16), nullable=False),
        sa.Column("stop_loss", sa.Numeric(24, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(24, 8), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["live_accounts.id"],
            name=op.f("fk_live_orders_account_id_live_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_orders")),
    )
    op.create_index(op.f("ix_live_orders_account_id"), "live_orders", ["account_id"], unique=False)
    op.create_index("ix_live_orders_account_status", "live_orders", ["account_id", "status"], unique=False)

    op.create_table(
        "live_activity_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp_label", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["live_accounts.id"],
            name=op.f("fk_live_activity_events_account_id_live_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_activity_events")),
    )
    op.create_index(op.f("ix_live_activity_events_account_id"), "live_activity_events", ["account_id"], unique=False)
    op.create_index(
        "ix_live_activity_account_created", "live_activity_events", ["account_id", "created_at"], unique=False
    )

    op.create_table(
        "live_guardian_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("action_label", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["live_accounts.id"],
            name=op.f("fk_live_guardian_alerts_account_id_live_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_guardian_alerts")),
    )
    op.create_index(op.f("ix_live_guardian_alerts_account_id"), "live_guardian_alerts", ["account_id"], unique=False)
    op.create_index("ix_live_guardian_account_sort", "live_guardian_alerts", ["account_id", "sort_order"], unique=False)

    op.create_table(
        "live_emergency_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_live_emergency_events_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_emergency_events")),
    )
    op.create_index(op.f("ix_live_emergency_events_user_id"), "live_emergency_events", ["user_id"], unique=False)
    op.create_index(
        "ix_live_emergency_user_created", "live_emergency_events", ["user_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_table("live_emergency_events")
    op.drop_table("live_guardian_alerts")
    op.drop_table("live_activity_events")
    op.drop_table("live_orders")
    op.drop_table("live_positions")
    op.drop_table("live_balances")
    op.drop_table("live_accounts")
