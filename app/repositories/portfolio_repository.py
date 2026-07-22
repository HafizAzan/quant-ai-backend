from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import (
    ActivityEvent,
    AiAnalysisSummary,
    AiRecommendation,
    AllocationSlice,
    Holding,
    MonthlyReturn,
    OpenPosition,
    PerformancePoint,
    Portfolio,
    PortfolioHealthMetric,
    PortfolioTimelineEvent,
    TradingSignal,
    WatchlistItem,
)


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> Portfolio | None:
        result = await self.session.execute(select(Portfolio).where(Portfolio.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_holdings(self, portfolio_id: UUID) -> list[Holding]:
        result = await self.session.execute(
            select(Holding).where(Holding.portfolio_id == portfolio_id).order_by(Holding.sort_order, Holding.symbol)
        )
        return list(result.scalars().all())

    async def get_holding(self, portfolio_id: UUID, holding_id: UUID) -> Holding | None:
        result = await self.session.execute(
            select(Holding).where(Holding.portfolio_id == portfolio_id, Holding.id == holding_id)
        )
        return result.scalar_one_or_none()

    async def list_open_positions(self, user_id: UUID) -> list[OpenPosition]:
        result = await self.session.execute(
            select(OpenPosition).where(OpenPosition.user_id == user_id).order_by(OpenPosition.sort_order)
        )
        return list(result.scalars().all())

    async def list_performance_points(
        self,
        user_id: UUID,
        range_key: str,
        series_kind: str | None = None,
    ) -> list[PerformancePoint]:
        stmt = select(PerformancePoint).where(
            PerformancePoint.user_id == user_id,
            PerformancePoint.range_key == range_key,
        )
        if series_kind:
            stmt = stmt.where(PerformancePoint.series_kind == series_kind)
        stmt = stmt.order_by(PerformancePoint.series_kind, PerformancePoint.time)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_allocation_slices(self, user_id: UUID, view: str | None = None) -> list[AllocationSlice]:
        stmt = select(AllocationSlice).where(AllocationSlice.user_id == user_id)
        if view:
            stmt = stmt.where(AllocationSlice.view == view)
        stmt = stmt.order_by(AllocationSlice.view, AllocationSlice.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_monthly_returns(self, user_id: UUID) -> list[MonthlyReturn]:
        result = await self.session.execute(
            select(MonthlyReturn).where(MonthlyReturn.user_id == user_id).order_by(MonthlyReturn.sort_order)
        )
        return list(result.scalars().all())

    async def list_health_metrics(self, user_id: UUID) -> list[PortfolioHealthMetric]:
        result = await self.session.execute(
            select(PortfolioHealthMetric)
            .where(PortfolioHealthMetric.user_id == user_id)
            .order_by(PortfolioHealthMetric.sort_order)
        )
        return list(result.scalars().all())

    async def list_recommendations(self, user_id: UUID) -> list[AiRecommendation]:
        result = await self.session.execute(
            select(AiRecommendation).where(AiRecommendation.user_id == user_id).order_by(AiRecommendation.sort_order)
        )
        return list(result.scalars().all())

    async def list_timeline(self, user_id: UUID) -> list[PortfolioTimelineEvent]:
        result = await self.session.execute(
            select(PortfolioTimelineEvent)
            .where(PortfolioTimelineEvent.user_id == user_id)
            .order_by(PortfolioTimelineEvent.sort_order)
        )
        return list(result.scalars().all())

    async def list_watchlist(self, user_id: UUID) -> list[WatchlistItem]:
        result = await self.session.execute(
            select(WatchlistItem).where(WatchlistItem.user_id == user_id).order_by(WatchlistItem.sort_order)
        )
        return list(result.scalars().all())

    async def list_activity(self, user_id: UUID, limit: int = 20) -> list[ActivityEvent]:
        result = await self.session.execute(
            select(ActivityEvent)
            .where(ActivityEvent.user_id == user_id)
            .order_by(ActivityEvent.sort_order)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_signals(self, user_id: UUID) -> list[TradingSignal]:
        result = await self.session.execute(
            select(TradingSignal)
            .where(TradingSignal.user_id == user_id, TradingSignal.is_active.is_(True))
            .order_by(TradingSignal.sort_order)
        )
        return list(result.scalars().all())

    async def list_ai_analyses(self, user_id: UUID, limit: int = 10) -> list[AiAnalysisSummary]:
        result = await self.session.execute(
            select(AiAnalysisSummary)
            .where(AiAnalysisSummary.user_id == user_id)
            .order_by(AiAnalysisSummary.sort_order)
            .limit(limit)
        )
        return list(result.scalars().all())
