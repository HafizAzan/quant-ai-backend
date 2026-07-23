from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, row: Notification) -> Notification:
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, user_id: UUID, notification_id: UUID) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        unread_only: bool,
        page: int,
        page_size: int,
    ) -> tuple[list[Notification], int]:
        filters = [Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.read_at.is_(None))
        total = await self.session.scalar(select(func.count()).select_from(Notification).where(*filters)) or 0
        result = await self.session.execute(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), int(total)

    async def unread_count(self, user_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            )
            or 0
        )

    async def mark_read(self, user_id: UUID, notification_id: UUID, when: datetime) -> Notification | None:
        row = await self.get(user_id, notification_id)
        if row is None:
            return None
        if row.read_at is None:
            row.read_at = when
            await self.session.flush()
        return row

    async def mark_all_read(self, user_id: UUID, when: datetime) -> int:
        result = await self.session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=when)
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def delete(self, row: Notification) -> None:
        await self.session.delete(row)
        await self.session.flush()
