from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatThread, CommandExecution


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, obj: object) -> None:
        self.session.add(obj)

    async def flush(self) -> None:
        await self.session.flush()

    async def delete(self, obj: object) -> None:
        await self.session.delete(obj)

    async def get_thread(self, user_id: UUID, thread_id: UUID) -> ChatThread | None:
        result = await self.session.execute(
            select(ChatThread)
            .options(selectinload(ChatThread.messages))
            .where(ChatThread.id == thread_id, ChatThread.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_threads(self, user_id: UUID, *, page: int = 1, page_size: int = 50) -> tuple[list[ChatThread], int]:
        filters = [ChatThread.user_id == user_id]
        total = int(
            (await self.session.execute(select(func.count()).select_from(ChatThread).where(*filters))).scalar_one()
        )
        result = await self.session.execute(
            select(ChatThread)
            .where(*filters)
            .order_by(ChatThread.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def list_messages(self, thread_id: UUID) -> list[ChatMessage]:
        result = await self.session.execute(
            select(ChatMessage).where(ChatMessage.thread_id == thread_id).order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def add_execution(self, execution: CommandExecution) -> None:
        self.session.add(execution)
