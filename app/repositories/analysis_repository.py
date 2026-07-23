from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AiAnalysis
from app.models.market import Asset, Candle


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, obj: AiAnalysis) -> None:
        self.session.add(obj)

    async def flush(self) -> None:
        await self.session.flush()

    async def get(self, user_id: UUID, analysis_id: UUID) -> AiAnalysis | None:
        result = await self.session.execute(
            select(AiAnalysis).where(AiAnalysis.id == analysis_id, AiAnalysis.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        saved_only: bool = False,
        symbol: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AiAnalysis], int]:
        filters = [AiAnalysis.user_id == user_id]
        if saved_only:
            filters.append(AiAnalysis.is_saved.is_(True))
        if symbol:
            filters.append(AiAnalysis.symbol == symbol)

        count_result = await self.session.execute(select(func.count()).select_from(AiAnalysis).where(*filters))
        total = int(count_result.scalar_one())

        result = await self.session.execute(
            select(AiAnalysis)
            .where(*filters)
            .order_by(AiAnalysis.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def latest_for_symbol(
        self,
        user_id: UUID,
        symbol: str,
        timeframe: str,
    ) -> AiAnalysis | None:
        result = await self.session.execute(
            select(AiAnalysis)
            .where(
                AiAnalysis.user_id == user_id,
                AiAnalysis.symbol == symbol,
                AiAnalysis.timeframe == timeframe,
            )
            .order_by(AiAnalysis.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete(self, analysis: AiAnalysis) -> None:
        await self.session.delete(analysis)

    async def get_asset(self, symbol: str) -> Asset | None:
        key = symbol.upper().replace("/", "").replace("-", "")
        result = await self.session.execute(
            select(Asset).where((Asset.trading_pair == key) | (Asset.symbol == key.replace("USDT", "")))
        )
        return result.scalar_one_or_none()

    async def list_candles(self, trading_pair: str, timeframe: str, limit: int) -> list[Candle]:
        result = await self.session.execute(
            select(Candle)
            .where(Candle.trading_pair == trading_pair, Candle.timeframe == timeframe)
            .order_by(Candle.open_time.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows
