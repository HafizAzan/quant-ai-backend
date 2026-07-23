from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class ChatThread(Base):
    __tablename__ = "chat_threads"
    __table_args__ = (Index("ix_chat_threads_user_updated", "user_id", "updated_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    preview: Mapped[str] = mapped_column(Text, nullable=False, default="")
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bias: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engine: Mapped[str] = mapped_column(String(64), nullable=False, default="GPT-4o-Market-Enhanced")
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=32000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_thread_created", "thread_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sections: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    blocks: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    command_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    stream_status: Mapped[str] = mapped_column(String(16), nullable=False, default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    thread: Mapped[ChatThread] = relationship(back_populates="messages")


class CommandExecution(Base):
    """Audit log of resolved platform commands from chat."""

    __tablename__ = "command_executions"
    __table_args__ = (Index("ix_command_executions_user_created", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    thread_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    message_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    command_id: Mapped[str] = mapped_column(String(64), nullable=False)
    raw: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    module: Mapped[str] = mapped_column(String(32), nullable=False)
    href: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
