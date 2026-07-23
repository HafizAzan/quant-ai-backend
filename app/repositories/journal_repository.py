from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.journal import JournalCoachItem, JournalEntry, JournalProfile, JournalTimelineEvent


class JournalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, obj: object) -> None:
        self.session.add(obj)

    async def flush(self) -> None:
        await self.session.flush()

    async def delete(self, obj: object) -> None:
        await self.session.delete(obj)

    async def get_profile(self, user_id: UUID) -> JournalProfile | None:
        result = await self.session.execute(select(JournalProfile).where(JournalProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_entry(self, user_id: UUID, entry_id: UUID) -> JournalEntry | None:
        result = await self.session.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.timeline))
            .where(JournalEntry.id == entry_id, JournalEntry.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_entries(
        self,
        user_id: UUID,
        *,
        date_range: str = "30d",
        asset: str | None = None,
        strategy: str | None = None,
        outcome: str | None = None,
        query: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[JournalEntry], int]:
        filters = [JournalEntry.user_id == user_id]

        if date_range != "all":
            days = {"7d": 7, "30d": 30, "90d": 90}.get(date_range, 30)
            since = datetime.now(timezone.utc) - timedelta(days=days)
            filters.append(JournalEntry.traded_at >= since)

        if asset and asset != "all":
            key = asset.upper().replace("/", "").replace("-", "").replace(" ", "")
            filters.append(
                or_(
                    JournalEntry.symbol == asset,
                    JournalEntry.symbol == key,
                    func.replace(func.upper(JournalEntry.symbol), "/", "") == key,
                )
            )
        if strategy and strategy != "all":
            filters.append(func.upper(JournalEntry.strategy_tag) == strategy.upper())
        if outcome and outcome != "all":
            filters.append(JournalEntry.outcome == outcome)
        if query:
            q = f"%{query.lower()}%"
            filters.append(
                or_(
                    func.lower(JournalEntry.symbol).like(q),
                    func.lower(JournalEntry.strategy_tag).like(q),
                    func.lower(JournalEntry.notes).like(q),
                    func.lower(func.coalesce(JournalEntry.emotion_tag, "")).like(q),
                )
            )

        total = int(
            (await self.session.execute(select(func.count()).select_from(JournalEntry).where(*filters))).scalar_one()
        )
        result = await self.session.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.timeline))
            .where(*filters)
            .order_by(JournalEntry.traded_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def list_coach(self, user_id: UUID) -> list[JournalCoachItem]:
        result = await self.session.execute(
            select(JournalCoachItem)
            .where(JournalCoachItem.user_id == user_id)
            .order_by(JournalCoachItem.sort_order)
        )
        return list(result.scalars().all())
