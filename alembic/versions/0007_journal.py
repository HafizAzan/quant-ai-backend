"""Journal tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_journal"
down_revision: Union[str, None] = "0006_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "journal_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.String(length=64), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("discipline", sa.Integer(), nullable=False),
        sa.Column("psychology", sa.Integer(), nullable=False),
        sa.Column("risk_management", sa.Integer(), nullable=False),
        sa.Column("execution", sa.Integer(), nullable=False),
        sa.Column("biggest_weakness", sa.String(length=255), nullable=False),
        sa.Column("current_mission", sa.Text(), nullable=False),
        sa.Column("estimated_improvement", sa.String(length=120), nullable=False),
        sa.Column("analytics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("patterns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("allocation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("monthly_progress", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("daily_pnl", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strategy_insight", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_journal_profiles_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_journal_profiles_user_id")),
    )
    op.create_index(op.f("ix_journal_profiles_user_id"), "journal_profiles", ["user_id"], unique=True)

    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("strategy_tag", sa.String(length=32), nullable=False),
        sa.Column("emotion_tag", sa.String(length=32), nullable=True),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("market_condition", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("pnl", sa.Numeric(24, 2), nullable=False),
        sa.Column("roi_percent", sa.Numeric(12, 4), nullable=False),
        sa.Column("risk_reward", sa.String(length=32), nullable=False),
        sa.Column("duration", sa.String(length=32), nullable=False),
        sa.Column("exited_at_label", sa.String(length=32), nullable=False),
        sa.Column("entry_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("exit_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(24, 8), nullable=False),
        sa.Column("take_profit", sa.Numeric(24, 8), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("psychology_notes", sa.Text(), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=False),
        sa.Column("score", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mistakes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("improvement", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("candles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("entry_time", sa.BigInteger(), nullable=False),
        sa.Column("exit_time", sa.BigInteger(), nullable=False),
        sa.Column("traded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("date_group", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_journal_entries_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_entries")),
    )
    op.create_index(op.f("ix_journal_entries_user_id"), "journal_entries", ["user_id"], unique=False)
    op.create_index(op.f("ix_journal_entries_symbol"), "journal_entries", ["symbol"], unique=False)
    op.create_index("ix_journal_entries_user_traded", "journal_entries", ["user_id", "traded_at"], unique=False)
    op.create_index("ix_journal_entries_user_outcome", "journal_entries", ["user_id", "outcome"], unique=False)

    op.create_table(
        "journal_timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("time_label", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["journal_entries.id"],
            name=op.f("fk_journal_timeline_events_entry_id_journal_entries"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_timeline_events")),
    )
    op.create_index(op.f("ix_journal_timeline_events_entry_id"), "journal_timeline_events", ["entry_id"], unique=False)
    op.create_index("ix_journal_timeline_sort", "journal_timeline_events", ["entry_id", "sort_order"], unique=False)

    op.create_table(
        "journal_coach_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("action_label", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_journal_coach_items_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journal_coach_items")),
    )
    op.create_index(op.f("ix_journal_coach_items_user_id"), "journal_coach_items", ["user_id"], unique=False)
    op.create_index("ix_journal_coach_user_sort", "journal_coach_items", ["user_id", "sort_order"], unique=False)


def downgrade() -> None:
    op.drop_table("journal_coach_items")
    op.drop_table("journal_timeline_events")
    op.drop_table("journal_entries")
    op.drop_table("journal_profiles")
