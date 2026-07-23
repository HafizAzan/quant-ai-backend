"""Strategies, canvas nodes/edges, and backtest runs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_strategies"
down_revision: Union[str, None] = "0008_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("markets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timeframes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("ai_confidence", sa.Integer(), nullable=False),
        sa.Column("estimated_risk", sa.String(length=16), nullable=False),
        sa.Column("estimated_monthly_return", sa.String(length=32), nullable=False),
        sa.Column("win_rate", sa.Numeric(8, 2), nullable=False),
        sa.Column("profit_factor", sa.Numeric(8, 2), nullable=False),
        sa.Column("drawdown", sa.Numeric(8, 2), nullable=False),
        sa.Column("max_drawdown", sa.Numeric(8, 2), nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("strategy_type", sa.String(length=64), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("last_backtest_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_backtest_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_strategies_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategies")),
    )
    op.create_index(op.f("ix_strategies_user_id"), "strategies", ["user_id"], unique=False)
    op.create_index("ix_strategies_user_updated", "strategies", ["user_id", "updated_at"], unique=False)
    op.create_index("ix_strategies_user_status", "strategies", ["user_id", "status"], unique=False)

    op.create_table(
        "strategy_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_key", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("type_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lines", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("collapsed", sa.Boolean(), nullable=False),
        sa.Column("validation", sa.String(length=16), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ports", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["strategy_id"],
            ["strategies.id"],
            name=op.f("fk_strategy_nodes_strategy_id_strategies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_nodes")),
    )
    op.create_index(op.f("ix_strategy_nodes_strategy_id"), "strategy_nodes", ["strategy_id"], unique=False)
    op.create_index("ix_strategy_nodes_strategy_sort", "strategy_nodes", ["strategy_id", "sort_order"], unique=False)

    op.create_table(
        "strategy_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_key", sa.String(length=64), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("target_key", sa.String(length=64), nullable=False),
        sa.Column("source_port", sa.String(length=32), nullable=True),
        sa.Column("target_port", sa.String(length=32), nullable=True),
        sa.Column("label", sa.String(length=32), nullable=True),
        sa.Column("highlighted", sa.Boolean(), nullable=False),
        sa.Column("errored", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["strategy_id"],
            ["strategies.id"],
            name=op.f("fk_strategy_edges_strategy_id_strategies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_edges")),
    )
    op.create_index(op.f("ix_strategy_edges_strategy_id"), "strategy_edges", ["strategy_id"], unique=False)
    op.create_index("ix_strategy_edges_strategy", "strategy_edges", ["strategy_id"], unique=False)

    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("range_label", sa.String(length=32), nullable=False),
        sa.Column("win_rate", sa.Numeric(8, 2), nullable=False),
        sa.Column("profit_factor", sa.Numeric(8, 2), nullable=False),
        sa.Column("drawdown", sa.Numeric(8, 2), nullable=False),
        sa.Column("sharpe", sa.Numeric(8, 2), nullable=False),
        sa.Column("trades", sa.Integer(), nullable=False),
        sa.Column("monthly_return", sa.String(length=32), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["strategy_id"],
            ["strategies.id"],
            name=op.f("fk_backtest_runs_strategy_id_strategies"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_backtest_runs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backtest_runs")),
    )
    op.create_index(op.f("ix_backtest_runs_strategy_id"), "backtest_runs", ["strategy_id"], unique=False)
    op.create_index(op.f("ix_backtest_runs_user_id"), "backtest_runs", ["user_id"], unique=False)
    op.create_index(
        "ix_backtest_runs_strategy_created", "backtest_runs", ["strategy_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_table("backtest_runs")
    op.drop_table("strategy_edges")
    op.drop_table("strategy_nodes")
    op.drop_table("strategies")
