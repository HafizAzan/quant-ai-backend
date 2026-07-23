from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange import ExchangeAccount


class ExchangeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_accounts(self, user_id: UUID) -> list[ExchangeAccount]:
        result = await self.session.execute(
            select(ExchangeAccount)
            .where(ExchangeAccount.user_id == user_id)
            .order_by(ExchangeAccount.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, user_id: UUID, account_id: UUID) -> ExchangeAccount | None:
        result = await self.session.execute(
            select(ExchangeAccount).where(ExchangeAccount.id == account_id, ExchangeAccount.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self, user_id: UUID) -> ExchangeAccount | None:
        result = await self.session.execute(
            select(ExchangeAccount)
            .where(ExchangeAccount.user_id == user_id, ExchangeAccount.is_active.is_(True))
            .order_by(ExchangeAccount.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def add(self, row: ExchangeAccount) -> ExchangeAccount:
        self.session.add(row)
        await self.session.flush()
        return row

    async def flush(self) -> None:
        await self.session.flush()
