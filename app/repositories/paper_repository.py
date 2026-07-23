from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Asset
from app.models.paper import (
    PaperAccount,
    PaperEquityPoint,
    PaperOrder,
    PaperPosition,
    PaperPositionEvent,
    PaperSentinelSuggestion,
)


class PaperRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_account_by_user(self, user_id: UUID) -> PaperAccount | None:
        result = await self.session.execute(select(PaperAccount).where(PaperAccount.user_id == user_id))
        return result.scalar_one_or_none()

    async def add(self, obj: object) -> None:
        self.session.add(obj)

    async def flush(self) -> None:
        await self.session.flush()

    async def list_open_positions(self, account_id: UUID) -> list[PaperPosition]:
        result = await self.session.execute(
            select(PaperPosition)
            .where(PaperPosition.account_id == account_id, PaperPosition.status == "open")
            .order_by(PaperPosition.opened_at.desc())
        )
        return list(result.scalars().all())

    async def list_closed_positions(self, account_id: UUID, limit: int = 50) -> list[PaperPosition]:
        result = await self.session.execute(
            select(PaperPosition)
            .where(PaperPosition.account_id == account_id, PaperPosition.status == "closed")
            .order_by(PaperPosition.closed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_position(self, account_id: UUID, position_id: UUID) -> PaperPosition | None:
        result = await self.session.execute(
            select(PaperPosition).where(PaperPosition.account_id == account_id, PaperPosition.id == position_id)
        )
        return result.scalar_one_or_none()

    async def list_pending_orders(self, account_id: UUID) -> list[PaperOrder]:
        result = await self.session.execute(
            select(PaperOrder)
            .where(PaperOrder.account_id == account_id, PaperOrder.status == "pending")
            .order_by(PaperOrder.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_order(self, account_id: UUID, order_id: UUID) -> PaperOrder | None:
        result = await self.session.execute(
            select(PaperOrder).where(PaperOrder.account_id == account_id, PaperOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    async def list_equity_points(self, account_id: UUID, range_key: str) -> list[PaperEquityPoint]:
        result = await self.session.execute(
            select(PaperEquityPoint)
            .where(PaperEquityPoint.account_id == account_id, PaperEquityPoint.range_key == range_key)
            .order_by(PaperEquityPoint.sort_order)
        )
        return list(result.scalars().all())

    async def list_position_events(self, position_id: UUID) -> list[PaperPositionEvent]:
        result = await self.session.execute(
            select(PaperPositionEvent)
            .where(PaperPositionEvent.position_id == position_id)
            .order_by(PaperPositionEvent.sort_order)
        )
        return list(result.scalars().all())

    async def get_sentinel(self, account_id: UUID) -> PaperSentinelSuggestion | None:
        result = await self.session.execute(
            select(PaperSentinelSuggestion).where(
                PaperSentinelSuggestion.account_id == account_id,
                PaperSentinelSuggestion.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_asset_price(self, symbol: str) -> Decimal | None:
        key = symbol.upper().replace("/", "").replace("-", "")
        result = await self.session.execute(
            select(Asset).where((Asset.trading_pair == key) | (Asset.symbol == key.replace("USDT", "")))
        )
        asset = result.scalar_one_or_none()
        return asset.price if asset else None
