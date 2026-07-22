from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Asset, Candle, MarketSnapshot, UserFavorite


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_query(self) -> Select[tuple[Asset]]:
        return select(Asset).where(Asset.is_active.is_(True))

    async def list_assets(
        self,
        *,
        tab: str = "all",
        category: str = "all",
        change: str = "any",
        search: str | None = None,
        favorite_asset_ids: set[UUID] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Asset], int]:
        query = self._base_query()

        if category != "all":
            query = query.where(Asset.category == category)

        if tab == "high-volume":
            query = query.where(Asset.is_high_volume.is_(True))
        elif tab == "new-listing":
            query = query.where(Asset.is_new_listing.is_(True))
        elif tab == "crypto-ai":
            query = query.where(Asset.is_crypto_ai.is_(True))
        elif tab == "favorites":
            if not favorite_asset_ids:
                return [], 0
            query = query.where(Asset.id.in_(favorite_asset_ids))

        if change == "up":
            query = query.where(Asset.change_24h > 0)
        elif change == "down":
            query = query.where(Asset.change_24h < 0)

        if search:
            like = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Asset.symbol.ilike(like),
                    Asset.name.ilike(like),
                    Asset.trading_pair.ilike(like),
                )
            )

        count_result = await self.session.execute(select(func.count()).select_from(query.subquery()))
        total = int(count_result.scalar_one())

        offset = max(page - 1, 0) * page_size
        result = await self.session.execute(
            query.order_by(Asset.rank.asc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_by_trading_pair(self, trading_pair: str) -> Asset | None:
        result = await self.session.execute(
            select(Asset).where(Asset.trading_pair == trading_pair.upper())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, asset_id: UUID) -> Asset | None:
        result = await self.session.execute(select(Asset).where(Asset.id == asset_id))
        return result.scalar_one_or_none()

    async def get_by_symbol(self, symbol: str) -> Asset | None:
        result = await self.session.execute(select(Asset).where(Asset.symbol == symbol.upper()))
        return result.scalar_one_or_none()


class CandleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_candles(
        self,
        *,
        trading_pair: str,
        timeframe: str,
        limit: int = 200,
    ) -> list[Candle]:
        result = await self.session.execute(
            select(Candle)
            .where(
                and_(
                    Candle.trading_pair == trading_pair.upper(),
                    Candle.timeframe == timeframe,
                )
            )
            .order_by(Candle.open_time.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows


class FavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_asset_ids(self, user_id: UUID) -> set[UUID]:
        result = await self.session.execute(
            select(UserFavorite.asset_id).where(UserFavorite.user_id == user_id)
        )
        return set(result.scalars().all())

    async def get(self, user_id: UUID, asset_id: UUID) -> UserFavorite | None:
        result = await self.session.execute(
            select(UserFavorite).where(
                UserFavorite.user_id == user_id,
                UserFavorite.asset_id == asset_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(self, user_id: UUID, asset_id: UUID) -> UserFavorite:
        row = UserFavorite(user_id=user_id, asset_id=asset_id)
        self.session.add(row)
        await self.session.flush()
        return row

    async def remove(self, row: UserFavorite) -> None:
        await self.session.delete(row)
        await self.session.flush()


class MarketSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest(self) -> MarketSnapshot | None:
        result = await self.session.execute(
            select(MarketSnapshot).order_by(MarketSnapshot.updated_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()
