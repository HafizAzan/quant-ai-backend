from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search import SearchPin, SearchRecent


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_recents(self, user_id: UUID, limit: int = 20) -> list[SearchRecent]:
        result = await self.session.execute(
            select(SearchRecent).where(SearchRecent.user_id == user_id).order_by(SearchRecent.at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def add_recent(self, row: SearchRecent) -> SearchRecent:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_pins(self, user_id: UUID) -> list[SearchPin]:
        result = await self.session.execute(
            select(SearchPin).where(SearchPin.user_id == user_id).order_by(SearchPin.sort_order.asc())
        )
        return list(result.scalars().all())

    async def get_pin(self, user_id: UUID, item_id: str) -> SearchPin | None:
        result = await self.session.execute(
            select(SearchPin).where(SearchPin.user_id == user_id, SearchPin.item_id == item_id)
        )
        return result.scalar_one_or_none()

    async def add_pin(self, row: SearchPin) -> SearchPin:
        self.session.add(row)
        await self.session.flush()
        return row

    async def delete_pin(self, user_id: UUID, item_id: str) -> bool:
        result = await self.session.execute(
            delete(SearchPin).where(SearchPin.user_id == user_id, SearchPin.item_id == item_id)
        )
        await self.session.flush()
        return bool(result.rowcount)
