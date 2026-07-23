"""Paper trading tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_paper"
down_revision: Union[str, None] = "0003_portfolio"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paper_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash", sa.Numeric(24, 2), nullable=False),
        sa.Column("equity", sa.Numeric(24, 2), nullable=False),
        sa.Column("starting_equity", sa.Numeric(24, 2), nullable=False),
        sa.Column("win_rate_percent", sa.Numeric(8, 2), nullable=False),
        sa.Column("total_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("max_drawdown_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("learning_mode", sa.String(length=16), nullable=False),
        sa.Column("fee_rate_bps", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_paper_accounts_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_accounts")),
        sa.UniqueConstraint("user_id", name=op.f("uq_paper_accounts_user_id")),
    )
    op.create_index(op.f("ix_paper_accounts_user_id"), "paper_accounts", ["user_id"], unique=True)

    op.create_table(
        "paper_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("order_type", sa.String(length=8), nullable=False),
        sa.Column("size", sa.Numeric(24, 8), nullable=False),
        sa.Column("size_label", sa.String(length=64), nullable=False),
        sa.Column("limit_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(24, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(24, 8), nullable=True),
        sa.Column("size_mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["paper_accounts.id"], name=op.f("fk_paper_orders_account_id_paper_accounts"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_orders")),
    )
    op.create_index(op.f("ix_paper_orders_account_id"), "paper_orders", ["account_id"], unique=False)
    op.create_index("ix_paper_orders_account_status", "paper_orders", ["account_id", "status"], unique=False)

    op.create_table(
        "paper_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("size", sa.Numeric(24, 8), nullable=False),
        sa.Column("size_label", sa.String(length=64), nullable=False),
        sa.Column("entry", sa.Numeric(24, 8), nullable=False),
        sa.Column("current", sa.Numeric(24, 8), nullable=False),
        sa.Column("exit_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(24, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(24, 8), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("health", sa.String(length=16), nullable=False),
        sa.Column("lifecycle", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ai_analysis", sa.Text(), nullable=False),
        sa.Column("future_commentary", sa.Text(), nullable=False),
        sa.Column("chart_snapshot_label", sa.String(length=120), nullable=False),
        sa.Column("risk_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trade_events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("execution_history", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["paper_accounts.id"],
            name=op.f("fk_paper_positions_account_id_paper_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["paper_orders.id"], name=op.f("fk_paper_positions_order_id_paper_orders"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_positions")),
    )
    op.create_index(op.f("ix_paper_positions_account_id"), "paper_positions", ["account_id"], unique=False)
    op.create_index("ix_paper_positions_account_status", "paper_positions", ["account_id", "status"], unique=False)

    op.create_table(
        "paper_fills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=False),
        sa.Column("fee", sa.Numeric(24, 8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["paper_accounts.id"], name=op.f("fk_paper_fills_account_id_paper_accounts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["paper_orders.id"], name=op.f("fk_paper_fills_order_id_paper_orders"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["paper_positions.id"],
            name=op.f("fk_paper_fills_position_id_paper_positions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_fills")),
    )
    op.create_index(op.f("ix_paper_fills_account_id"), "paper_fills", ["account_id"], unique=False)
    op.create_index(op.f("ix_paper_fills_order_id"), "paper_fills", ["order_id"], unique=False)
    op.create_index("ix_paper_fills_account_created", "paper_fills", ["account_id", "created_at"], unique=False)

    op.create_table(
        "paper_equity_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("range_key", sa.String(length=8), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(24, 8), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["paper_accounts.id"],
            name=op.f("fk_paper_equity_points_account_id_paper_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_equity_points")),
    )
    op.create_index(op.f("ix_paper_equity_points_account_id"), "paper_equity_points", ["account_id"], unique=False)
    op.create_index("ix_paper_equity_account_range", "paper_equity_points", ["account_id", "range_key"], unique=False)

    op.create_table(
        "paper_position_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("time_label", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["paper_positions.id"],
            name=op.f("fk_paper_position_events_position_id_paper_positions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_position_events")),
    )
    op.create_index(op.f("ix_paper_position_events_position_id"), "paper_position_events", ["position_id"], unique=False)
    op.create_index("ix_paper_pos_events_sort", "paper_position_events", ["position_id", "sort_order"], unique=False)

    op.create_table(
        "paper_sentinel_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("suggested_tp", sa.Numeric(24, 8), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["paper_accounts.id"],
            name=op.f("fk_paper_sentinel_suggestions_account_id_paper_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_sentinel_suggestions")),
        sa.UniqueConstraint("account_id", name="uq_paper_sentinel_account"),
    )


def downgrade() -> None:
    op.drop_table("paper_sentinel_suggestions")
    op.drop_table("paper_position_events")
    op.drop_table("paper_equity_points")
    op.drop_table("paper_fills")
    op.drop_table("paper_positions")
    op.drop_table("paper_orders")
    op.drop_table("paper_accounts")
