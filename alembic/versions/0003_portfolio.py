"""Dashboard + Portfolio tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_portfolio"
down_revision: Union[str, None] = "0002_markets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_balance", sa.Numeric(24, 2), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("realized_pnl_ytd", sa.Numeric(24, 2), nullable=False),
        sa.Column("equity", sa.Numeric(24, 2), nullable=False),
        sa.Column("change_24h_percent", sa.Numeric(12, 4), nullable=False),
        sa.Column("mtd_percent", sa.Numeric(12, 4), nullable=False),
        sa.Column("daily_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("weekly_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("weekly_target_percent", sa.Numeric(8, 2), nullable=False),
        sa.Column("ai_confidence_percent", sa.Numeric(8, 2), nullable=False),
        sa.Column("ai_confidence_label", sa.String(length=64), nullable=False),
        sa.Column("win_rate_percent", sa.Numeric(8, 2), nullable=False),
        sa.Column("win_rate_period", sa.String(length=64), nullable=False),
        sa.Column("win_streak", sa.String(length=64), nullable=False),
        sa.Column("profit_factor", sa.Numeric(12, 4), nullable=False),
        sa.Column("balance_spark", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_score_overall", sa.Integer(), nullable=False),
        sa.Column("ai_score_risk", sa.String(length=32), nullable=False),
        sa.Column("ai_score_diversification", sa.String(length=32), nullable=False),
        sa.Column("ai_score_liquidity", sa.String(length=32), nullable=False),
        sa.Column("ai_score_volatility", sa.String(length=32), nullable=False),
        sa.Column("ai_score_capital_allocation", sa.String(length=32), nullable=False),
        sa.Column("ai_score_recommendation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_portfolios_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_portfolios")),
        sa.UniqueConstraint("user_id", name=op.f("uq_portfolios_user_id")),
    )
    op.create_index(op.f("ix_portfolios_user_id"), "portfolios", ["user_id"], unique=True)

    op.create_table(
        "holdings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=False),
        sa.Column("value", sa.Numeric(24, 2), nullable=False),
        sa.Column("pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("allocation", sa.Numeric(8, 2), nullable=False),
        sa.Column("avg_entry", sa.Numeric(24, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("ai_analysis", sa.Text(), nullable=False),
        sa.Column("risk_assessment", sa.Text(), nullable=False),
        sa.Column("suggested_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trade_history", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["portfolio_id"],
            ["portfolios.id"],
            name=op.f("fk_holdings_portfolio_id_portfolios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_holdings")),
        sa.UniqueConstraint("portfolio_id", "symbol", name="uq_holdings_portfolio_symbol"),
    )
    op.create_index(op.f("ix_holdings_portfolio_id"), "holdings", ["portfolio_id"], unique=False)
    op.create_index("ix_holdings_portfolio_symbol", "holdings", ["portfolio_id", "symbol"], unique=False)

    op.create_table(
        "open_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("leverage", sa.String(length=16), nullable=False),
        sa.Column("size", sa.String(length=64), nullable=False),
        sa.Column("entry", sa.Numeric(24, 8), nullable=False),
        sa.Column("mark", sa.Numeric(24, 8), nullable=False),
        sa.Column("pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("pnl_percent", sa.Numeric(12, 4), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_open_positions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_open_positions")),
    )
    op.create_index(op.f("ix_open_positions_user_id"), "open_positions", ["user_id"], unique=False)
    op.create_index("ix_open_positions_user_sort", "open_positions", ["user_id", "sort_order"], unique=False)

    op.create_table(
        "performance_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("range_key", sa.String(length=8), nullable=False),
        sa.Column("series_kind", sa.String(length=32), nullable=False),
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("value", sa.Numeric(24, 8), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_performance_points_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_performance_points")),
    )
    op.create_index(op.f("ix_performance_points_user_id"), "performance_points", ["user_id"], unique=False)
    op.create_index(
        "ix_perf_user_range_series_time",
        "performance_points",
        ["user_id", "range_key", "series_kind", "time"],
        unique=False,
    )

    op.create_table(
        "allocation_slices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("view", sa.String(length=32), nullable=False),
        sa.Column("slice_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("percent", sa.Numeric(8, 2), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_allocation_slices_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_allocation_slices")),
    )
    op.create_index(op.f("ix_allocation_slices_user_id"), "allocation_slices", ["user_id"], unique=False)
    op.create_index("ix_allocation_user_view", "allocation_slices", ["user_id", "view"], unique=False)

    op.create_table(
        "monthly_returns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_key", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=16), nullable=False),
        sa.Column("value", sa.Numeric(8, 2), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_monthly_returns_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monthly_returns")),
        sa.UniqueConstraint("user_id", "period_key", name="uq_monthly_returns_user_period"),
    )
    op.create_index(op.f("ix_monthly_returns_user_id"), "monthly_returns", ["user_id"], unique=False)

    op.create_table(
        "portfolio_health_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("value", sa.String(length=64), nullable=False),
        sa.Column("tone", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_portfolio_health_metrics_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_portfolio_health_metrics")),
    )
    op.create_index(op.f("ix_portfolio_health_metrics_user_id"), "portfolio_health_metrics", ["user_id"], unique=False)
    op.create_index("ix_health_user_sort", "portfolio_health_metrics", ["user_id", "sort_order"], unique=False)

    op.create_table(
        "ai_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_ai_recommendations_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_recommendations")),
    )
    op.create_index(op.f("ix_ai_recommendations_user_id"), "ai_recommendations", ["user_id"], unique=False)
    op.create_index("ix_ai_rec_user_sort", "ai_recommendations", ["user_id", "sort_order"], unique=False)

    op.create_table(
        "portfolio_timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("time_label", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_portfolio_timeline_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_portfolio_timeline_events")),
    )
    op.create_index(
        op.f("ix_portfolio_timeline_events_user_id"), "portfolio_timeline_events", ["user_id"], unique=False
    )
    op.create_index("ix_timeline_user_sort", "portfolio_timeline_events", ["user_id", "sort_order"], unique=False)

    op.create_table(
        "watchlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=False),
        sa.Column("change_percent", sa.Numeric(12, 4), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_watchlist_items_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_watchlist_items")),
        sa.UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )
    op.create_index(op.f("ix_watchlist_items_user_id"), "watchlist_items", ["user_id"], unique=False)
    op.create_index("ix_watchlist_user_sort", "watchlist_items", ["user_id", "sort_order"], unique=False)

    op.create_table(
        "activity_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("time_label", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_activity_events_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_events")),
    )
    op.create_index(op.f("ix_activity_events_user_id"), "activity_events", ["user_id"], unique=False)
    op.create_index("ix_activity_user_sort", "activity_events", ["user_id", "sort_order"], unique=False)

    op.create_table(
        "trading_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pair", sa.String(length=64), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("entry", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=64), nullable=False),
        sa.Column("position", sa.String(length=16), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_trading_signals_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trading_signals")),
    )
    op.create_index(op.f("ix_trading_signals_user_id"), "trading_signals", ["user_id"], unique=False)
    op.create_index("ix_signals_user_sort", "trading_signals", ["user_id", "sort_order"], unique=False)

    op.create_table(
        "ai_analysis_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticker", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_ai_analysis_summaries_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_analysis_summaries")),
    )
    op.create_index(op.f("ix_ai_analysis_summaries_user_id"), "ai_analysis_summaries", ["user_id"], unique=False)
    op.create_index("ix_ai_analysis_user_sort", "ai_analysis_summaries", ["user_id", "sort_order"], unique=False)


def downgrade() -> None:
    op.drop_table("ai_analysis_summaries")
    op.drop_table("trading_signals")
    op.drop_table("activity_events")
    op.drop_table("watchlist_items")
    op.drop_table("portfolio_timeline_events")
    op.drop_table("ai_recommendations")
    op.drop_table("portfolio_health_metrics")
    op.drop_table("monthly_returns")
    op.drop_table("allocation_slices")
    op.drop_table("performance_points")
    op.drop_table("open_positions")
    op.drop_table("holdings")
    op.drop_table("portfolios")
