"""Search recents and pins for command palette."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_search"
down_revision: Union[str, None] = "0012_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_recents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.String(length=255), nullable=False),
        sa.Column("item_id", sa.String(length=120), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("href", sa.String(length=255), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_search_recents_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_recents")),
    )
    op.create_index(op.f("ix_search_recents_user_id"), "search_recents", ["user_id"], unique=False)
    op.create_index("ix_search_recents_user_at", "search_recents", ["user_id", "at"], unique=False)

    op.create_table(
        "search_pins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("href", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_search_pins_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_pins")),
        sa.UniqueConstraint("user_id", "item_id", name="uq_search_pins_user_item"),
    )
    op.create_index(op.f("ix_search_pins_user_id"), "search_pins", ["user_id"], unique=False)
    op.create_index("ix_search_pins_user_sort", "search_pins", ["user_id", "sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_search_pins_user_sort", table_name="search_pins")
    op.drop_index(op.f("ix_search_pins_user_id"), table_name="search_pins")
    op.drop_table("search_pins")
    op.drop_index("ix_search_recents_user_at", table_name="search_recents")
    op.drop_index(op.f("ix_search_recents_user_id"), table_name="search_recents")
    op.drop_table("search_recents")
