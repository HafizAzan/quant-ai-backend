from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import (
    Alert,
    AlertTimelineEvent,
    AlertTrigger,
    AlertWatchItem,
    NotificationChannel,
)
from app.models.market import Asset


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, obj: object) -> None:
        self.session.add(obj)

    async def flush(self) -> None:
        await self.session.flush()

    async def delete(self, obj: object) -> None:
        await self.session.delete(obj)

    async def get(self, user_id: UUID, alert_id: UUID) -> Alert | None:
        result = await self.session.execute(
            select(Alert)
            .options(selectinload(Alert.conditions), selectinload(Alert.timeline))
            .where(Alert.id == alert_id, Alert.user_id == user_id, Alert.status != "deleted")
        )
        return result.scalar_one_or_none()

    async def list_alerts(
        self,
        user_id: UUID,
        *,
        tab: str = "all",
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Alert], int]:
        filters = [Alert.user_id == user_id, Alert.status != "deleted", Alert.status != "archived"]
        if tab == "price":
            filters.append(Alert.category == "price")
        elif tab == "technical":
            filters.append(Alert.category == "technical")
        elif tab == "ai":
            filters.append(
                Alert.category.in_(
                    ["ai_signal", "bos", "choch", "liquidity_sweep", "demand_zone", "supply_zone", "fvg"]
                )
            )
        if search:
            q = f"%{search.lower()}%"
            filters.append(or_(func.lower(Alert.symbol).like(q), func.lower(Alert.title).like(q)))

        total = int(
            (await self.session.execute(select(func.count()).select_from(Alert).where(*filters))).scalar_one()
        )
        result = await self.session.execute(
            select(Alert)
            .options(selectinload(Alert.conditions), selectinload(Alert.timeline))
            .where(*filters)
            .order_by(Alert.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def list_enabled_price_alerts(self, user_id: UUID) -> list[Alert]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Alert)
            .options(selectinload(Alert.conditions))
            .where(
                Alert.user_id == user_id,
                Alert.enabled.is_(True),
                Alert.status == "active",
                Alert.category == "price",
                or_(Alert.muted_until.is_(None), Alert.muted_until < now),
            )
        )
        return list(result.scalars().all())

    async def count_active(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Alert).where(
                Alert.user_id == user_id,
                Alert.enabled.is_(True),
                Alert.status == "active",
            )
        )
        return int(result.scalar_one())

    async def count_triggers_since(self, user_id: UUID, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(AlertTrigger).where(
                AlertTrigger.user_id == user_id,
                AlertTrigger.created_at >= since,
            )
        )
        return int(result.scalar_one())

    async def list_triggers(self, user_id: UUID, limit: int = 20) -> list[AlertTrigger]:
        result = await self.session.execute(
            select(AlertTrigger)
            .where(AlertTrigger.user_id == user_id)
            .order_by(AlertTrigger.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_channels(self, user_id: UUID) -> list[NotificationChannel]:
        result = await self.session.execute(
            select(NotificationChannel).where(NotificationChannel.user_id == user_id).order_by(NotificationChannel.kind)
        )
        return list(result.scalars().all())

    async def get_channel(self, user_id: UUID, channel_id: UUID) -> NotificationChannel | None:
        result = await self.session.execute(
            select(NotificationChannel).where(
                NotificationChannel.id == channel_id,
                NotificationChannel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_watch_items(self, user_id: UUID) -> list[AlertWatchItem]:
        result = await self.session.execute(
            select(AlertWatchItem).where(AlertWatchItem.user_id == user_id).order_by(AlertWatchItem.sort_order)
        )
        return list(result.scalars().all())

    async def get_asset_price(self, symbol: str) -> Decimal | None:
        key = symbol.upper().replace("/", "").replace("-", "")
        result = await self.session.execute(
            select(Asset).where((Asset.trading_pair == key) | (Asset.symbol == key.replace("USDT", "")))
        )
        asset = result.scalar_one_or_none()
        return asset.price if asset else None

    async def next_timeline_order(self, alert_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(AlertTimelineEvent.sort_order), -1)).where(
                AlertTimelineEvent.alert_id == alert_id
            )
        )
        return int(result.scalar_one()) + 1
