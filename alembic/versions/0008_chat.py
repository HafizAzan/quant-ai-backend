"""AI Chat threads, messages, and command executions."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_chat"
down_revision: Union[str, None] = "0007_journal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("preview", sa.Text(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("bias", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("engine", sa.String(length=64), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("tokens_limit", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_chat_threads_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_threads")),
    )
    op.create_index(op.f("ix_chat_threads_user_id"), "chat_threads", ["user_id"], unique=False)
    op.create_index("ix_chat_threads_user_updated", "chat_threads", ["user_id", "updated_at"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("image_label", sa.String(length=255), nullable=True),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("command_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("stream_status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["chat_threads.id"],
            name=op.f("fk_chat_messages_thread_id_chat_threads"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
    )
    op.create_index(op.f("ix_chat_messages_thread_id"), "chat_messages", ["thread_id"], unique=False)
    op.create_index("ix_chat_messages_thread_created", "chat_messages", ["thread_id", "created_at"], unique=False)

    op.create_table(
        "command_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("command_id", sa.String(length=64), nullable=False),
        sa.Column("raw", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("module", sa.String(length=32), nullable=False),
        sa.Column("href", sa.String(length=120), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_command_executions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_command_executions")),
    )
    op.create_index(op.f("ix_command_executions_user_id"), "command_executions", ["user_id"], unique=False)
    op.create_index(
        "ix_command_executions_user_created", "command_executions", ["user_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_table("command_executions")
    op.drop_table("chat_messages")
    op.drop_table("chat_threads")
