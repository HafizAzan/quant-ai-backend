"""AI analysis tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_analysis"
down_revision: Union[str, None] = "0004_paper"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("lookback", sa.Integer(), nullable=False),
        sa.Column("open_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("high_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("low_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("close_price", sa.Numeric(24, 8), nullable=False),
        sa.Column("change_percent", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume_label", sa.String(length=32), nullable=False),
        sa.Column("ai_zones_label", sa.String(length=120), nullable=False),
        sa.Column("trend", sa.String(length=32), nullable=False),
        sa.Column("structure", sa.String(length=64), nullable=False),
        sa.Column("structure_note", sa.String(length=255), nullable=False),
        sa.Column("resistance_label", sa.String(length=120), nullable=False),
        sa.Column("resistance_range", sa.String(length=64), nullable=False),
        sa.Column("resistance_strength", sa.Integer(), nullable=False),
        sa.Column("support_label", sa.String(length=120), nullable=False),
        sa.Column("support_range", sa.String(length=64), nullable=False),
        sa.Column("support_strength", sa.Integer(), nullable=False),
        sa.Column("risk_reward_ratio", sa.String(length=32), nullable=False),
        sa.Column("risk_reward_probability", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("reasoning_title", sa.String(length=120), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("entry", sa.Numeric(24, 8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(24, 8), nullable=False),
        sa.Column("take_profit", sa.Numeric(24, 8), nullable=False),
        sa.Column("overlays", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_saved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_ai_analyses_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_analyses")),
    )
    op.create_index(op.f("ix_ai_analyses_user_id"), "ai_analyses", ["user_id"], unique=False)
    op.create_index(op.f("ix_ai_analyses_symbol"), "ai_analyses", ["symbol"], unique=False)
    op.create_index("ix_ai_analyses_user_symbol_tf", "ai_analyses", ["user_id", "symbol", "timeframe"], unique=False)
    op.create_index("ix_ai_analyses_user_saved", "ai_analyses", ["user_id", "is_saved", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("ai_analyses")
