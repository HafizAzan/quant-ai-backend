from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Asset
from app.repositories.market_repository import (
    AssetRepository,
    CandleRepository,
    FavoriteRepository,
    MarketSnapshotRepository,
)
from app.schemas.market import (
    CandleOut,
    CandlesData,
    FavoriteToggleOut,
    MarketAiPickOut,
    MarketAssetOut,
    MarketDominanceOut,
    MarketSentimentOut,
    MarketsListData,
    MarketsMetaOut,
)

ALLOWED_TIMEFRAMES = {"1m", "5m", "15m", "1h", "4h", "1d", "1w"}


class MarketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assets = AssetRepository(session)
        self.candles = CandleRepository(session)
        self.favorites = FavoriteRepository(session)
        self.snapshots = MarketSnapshotRepository(session)

    async def list_markets(
        self,
        *,
        tab: str = "all",
        category: str = "all",
        change: str = "any",
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        user_id: UUID | None = None,
    ) -> MarketsListData:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)

        favorite_ids: set[UUID] = set()
        if user_id is not None:
            favorite_ids = await self.favorites.list_asset_ids(user_id)

        rows, total = await self.assets.list_assets(
            tab=tab,
            category=category,
            change=change,
            search=search,
            favorite_asset_ids=favorite_ids if tab == "favorites" else None,
            page=page,
            page_size=page_size,
        )

        total_pages = ceil(total / page_size) if total else 0
        from_index = 0 if total == 0 else (page - 1) * page_size + 1
        to_index = 0 if total == 0 else min(page * page_size, total)

        items = [
            self._to_asset_out(asset, favorite=asset.id in favorite_ids)
            for asset in rows
        ]
        return MarketsListData(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            from_index=from_index,
            to_index=to_index,
        )

    async def get_meta(self) -> MarketsMetaOut:
        snapshot = await self.snapshots.get_latest()
        if snapshot is None:
            return MarketsMetaOut(
                sentiment=MarketSentimentOut(
                    score=50,
                    zone="Neutral",
                    description="Market snapshot not seeded yet.",
                ),
                dominance=MarketDominanceOut(
                    btc_percent=0,
                    alts_percent=0,
                    stables_percent=0,
                ),
                ai_pick=None,
            )

        ai_pick = None
        if snapshot.ai_pick_symbol and snapshot.ai_pick_confidence is not None:
            asset = await self.assets.get_by_symbol(snapshot.ai_pick_symbol)
            name = f"{asset.name} ({asset.symbol})" if asset else snapshot.ai_pick_symbol
            ai_pick = MarketAiPickOut(
                name=name,
                symbol=snapshot.ai_pick_symbol,
                confidence=snapshot.ai_pick_confidence,
            )

        return MarketsMetaOut(
            sentiment=MarketSentimentOut(
                score=snapshot.fear_greed_score,
                zone=snapshot.fear_greed_zone,
                description=snapshot.fear_greed_description,
            ),
            dominance=MarketDominanceOut(
                btc_percent=snapshot.btc_dominance,
                alts_percent=snapshot.alts_dominance,
                stables_percent=snapshot.stables_dominance,
            ),
            ai_pick=ai_pick,
        )

    async def get_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        limit: int = 200,
    ) -> CandlesData:
        timeframe = timeframe.lower()
        if timeframe not in ALLOWED_TIMEFRAMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timeframe. Allowed: {sorted(ALLOWED_TIMEFRAMES)}",
            )

        trading_pair = symbol.upper().replace("/", "").replace(" ", "")
        if not trading_pair.endswith("USDT") and len(trading_pair) <= 5:
            trading_pair = f"{trading_pair}USDT"

        asset = await self.assets.get_by_trading_pair(trading_pair)
        if asset is None:
            # also try bare symbol map BTC -> BTCUSDT
            asset = await self.assets.get_by_symbol(symbol.upper().replace("USDT", ""))
            if asset:
                trading_pair = asset.trading_pair

        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")

        limit = min(max(limit, 1), 1000)
        rows = await self.candles.list_candles(
            trading_pair=trading_pair,
            timeframe=timeframe,
            limit=limit,
        )
        return CandlesData(
            symbol=trading_pair,
            timeframe=timeframe,
            candles=[
                CandleOut(
                    time=row.open_time,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.volume,
                )
                for row in rows
            ],
        )

    async def toggle_favorite(self, user_id: UUID, asset_id: UUID) -> FavoriteToggleOut:
        asset = await self.assets.get_by_id(asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

        existing = await self.favorites.get(user_id, asset_id)
        if existing:
            await self.favorites.remove(existing)
            return FavoriteToggleOut(asset_id=asset_id, favorite=False)

        await self.favorites.add(user_id, asset_id)
        return FavoriteToggleOut(asset_id=asset_id, favorite=True)

    @staticmethod
    def _to_asset_out(asset: Asset, *, favorite: bool) -> MarketAssetOut:
        return MarketAssetOut(
            id=asset.id,
            symbol=asset.symbol,
            trading_pair=asset.trading_pair,
            name=asset.name,
            category=asset.category,
            rank=asset.rank,
            price=asset.price,
            change_24h=asset.change_24h,
            volume_24h=asset.volume_24h,
            market_cap=asset.market_cap,
            ai_signal=asset.ai_signal,
            color=asset.color,
            is_high_volume=asset.is_high_volume,
            is_new_listing=asset.is_new_listing,
            is_crypto_ai=asset.is_crypto_ai,
            favorite=favorite,
            pair_label=f"{asset.symbol} / USD",
        )
