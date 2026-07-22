"""Markets tables: assets, candles, user_favorites, market_snapshots."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_markets"
down_revision: Union[str, None] = "0001_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("trading_pair", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=False),
        sa.Column("change_24h", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume_24h", sa.Numeric(24, 2), nullable=False),
        sa.Column("market_cap", sa.Numeric(28, 2), nullable=False),
        sa.Column("ai_signal", sa.String(length=32), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("is_high_volume", sa.Boolean(), nullable=False),
        sa.Column("is_new_listing", sa.Boolean(), nullable=False),
        sa.Column("is_crypto_ai", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
        sa.UniqueConstraint("symbol", name=op.f("uq_assets_symbol")),
        sa.UniqueConstraint("trading_pair", name=op.f("uq_assets_trading_pair")),
    )
    op.create_index(op.f("ix_assets_symbol"), "assets", ["symbol"], unique=True)
    op.create_index(op.f("ix_assets_trading_pair"), "assets", ["trading_pair"], unique=True)
    op.create_index(op.f("ix_assets_category"), "assets", ["category"], unique=False)
    op.create_index(op.f("ix_assets_rank"), "assets", ["rank"], unique=False)

    op.create_table(
        "candles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trading_pair", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("open_time", sa.BigInteger(), nullable=False),
        sa.Column("open", sa.Numeric(24, 8), nullable=False),
        sa.Column("high", sa.Numeric(24, 8), nullable=False),
        sa.Column("low", sa.Numeric(24, 8), nullable=False),
        sa.Column("close", sa.Numeric(24, 8), nullable=False),
        sa.Column("volume", sa.Numeric(24, 8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name=op.f("fk_candles_asset_id_assets"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candles")),
        sa.UniqueConstraint("trading_pair", "timeframe", "open_time", name="uq_candles_pair_tf_time"),
    )
    op.create_index(op.f("ix_candles_asset_id"), "candles", ["asset_id"], unique=False)
    op.create_index("ix_candles_pair_tf_time", "candles", ["trading_pair", "timeframe", "open_time"], unique=False)

    op.create_table(
        "user_favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name=op.f("fk_user_favorites_asset_id_assets"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_favorites_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_favorites")),
        sa.UniqueConstraint("user_id", "asset_id", name="uq_user_favorites_user_asset"),
    )
    op.create_index(op.f("ix_user_favorites_user_id"), "user_favorites", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_favorites_asset_id"), "user_favorites", ["asset_id"], unique=False)

    op.create_table(
        "market_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fear_greed_score", sa.Integer(), nullable=False),
        sa.Column("fear_greed_zone", sa.String(length=32), nullable=False),
        sa.Column("fear_greed_description", sa.String(length=255), nullable=False),
        sa.Column("btc_dominance", sa.Numeric(8, 2), nullable=False),
        sa.Column("alts_dominance", sa.Numeric(8, 2), nullable=False),
        sa.Column("stables_dominance", sa.Numeric(8, 2), nullable=False),
        sa.Column("ai_pick_symbol", sa.String(length=32), nullable=True),
        sa.Column("ai_pick_confidence", sa.Numeric(8, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_snapshots")),
    )


def downgrade() -> None:
    op.drop_table("market_snapshots")
    op.drop_index(op.f("ix_user_favorites_asset_id"), table_name="user_favorites")
    op.drop_index(op.f("ix_user_favorites_user_id"), table_name="user_favorites")
    op.drop_table("user_favorites")
    op.drop_index("ix_candles_pair_tf_time", table_name="candles")
    op.drop_index(op.f("ix_candles_asset_id"), table_name="candles")
    op.drop_table("candles")
    op.drop_index(op.f("ix_assets_rank"), table_name="assets")
    op.drop_index(op.f("ix_assets_category"), table_name="assets")
    op.drop_index(op.f("ix_assets_trading_pair"), table_name="assets")
    op.drop_index(op.f("ix_assets_symbol"), table_name="assets")
    op.drop_table("assets")
