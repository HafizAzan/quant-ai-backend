from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.live import (
    LiveAccount,
    LiveActivityEvent,
    LiveBalance,
    LiveEmergencyEvent,
    LiveGuardianAlert,
    LiveOrder,
    LivePosition,
)


class LiveRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, obj: object) -> None:
        self.session.add(obj)

    async def flush(self) -> None:
        await self.session.flush()

    async def delete(self, obj: object) -> None:
        await self.session.delete(obj)

    async def get_account(self, user_id: UUID) -> LiveAccount | None:
        result = await self.session.execute(
            select(LiveAccount)
            .options(
                selectinload(LiveAccount.balances),
                selectinload(LiveAccount.positions),
                selectinload(LiveAccount.orders),
                selectinload(LiveAccount.activities),
                selectinload(LiveAccount.guardian_alerts),
            )
            .where(LiveAccount.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_position(self, account_id: UUID, position_id: UUID) -> LivePosition | None:
        result = await self.session.execute(
            select(LivePosition).where(
                LivePosition.id == position_id,
                LivePosition.account_id == account_id,
                LivePosition.status == "open",
            )
        )
        return result.scalar_one_or_none()

    async def get_order(self, account_id: UUID, order_id: UUID) -> LiveOrder | None:
        result = await self.session.execute(
            select(LiveOrder).where(LiveOrder.id == order_id, LiveOrder.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def list_open_orders(self, account_id: UUID) -> list[LiveOrder]:
        result = await self.session.execute(
            select(LiveOrder)
            .where(LiveOrder.account_id == account_id, LiveOrder.status == "open")
            .order_by(LiveOrder.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_open_positions(self, account_id: UUID) -> list[LivePosition]:
        result = await self.session.execute(
            select(LivePosition)
            .where(LivePosition.account_id == account_id, LivePosition.status == "open")
            .order_by(LivePosition.opened_at.desc())
        )
        return list(result.scalars().all())
