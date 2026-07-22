from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import (
    ActiveSignalOut,
    ActivityEventOut,
    AiAnalysisSummaryOut,
    AiConfidenceOut,
    AiPortfolioScoreOut,
    AiRecommendationOut,
    AllocationSliceOut,
    AssetDetailOut,
    DashboardSnapshotOut,
    HoldingOut,
    MonthlyReturnOut,
    OpenPositionOut,
    PerformanceSeriesOut,
    PnlPerformanceOut,
    PortfolioBalanceOut,
    PortfolioHealthMetricOut,
    PortfolioMetricOut,
    PortfolioOverviewOut,
    PortfolioPointOut,
    PortfolioTimelineEventOut,
    WatchlistItemOut,
    WinRateOut,
)

ALLOWED_RANGES = {"1D", "1W", "1M", "1Y", "ALL"}
ALLOWED_SERIES = {"equity", "unrealized", "realized", "balance", "benchmark"}


def _fmt_money(value: Decimal) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}${value:,.2f}"


def _quantity_label(quantity: Decimal) -> str:
    q = f"{quantity:,.8f}".rstrip("0").rstrip(".")
    if "." not in q:
        return f"{int(quantity):,}.00"
    return q


class PortfolioService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PortfolioRepository(session)

    async def get_dashboard(self, user_id: UUID) -> DashboardSnapshotOut:
        portfolio = await self.repo.get_by_user_id(user_id)
        if portfolio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        signals = await self.repo.list_signals(user_id)
        positions = await self.repo.list_open_positions(user_id)
        watchlist = await self.repo.list_watchlist(user_id)
        activity = await self.repo.list_activity(user_id)
        analyses = await self.repo.list_ai_analyses(user_id)

        spark = [float(x) for x in (portfolio.balance_spark or [])]

        return DashboardSnapshotOut(
            portfolio_balance=PortfolioBalanceOut(
                amount=portfolio.total_balance,
                percentage=portfolio.mtd_percent,
                percentage_label="MTD",
                chart_data=spark,
            ),
            pnl_performance=PnlPerformanceOut(
                daily_pnl=portfolio.daily_pnl,
                weekly_pnl=portfolio.weekly_pnl,
                weekly_target_percent=portfolio.weekly_target_percent,
            ),
            ai_confidence=AiConfidenceOut(
                percent=portfolio.ai_confidence_percent,
                label=portfolio.ai_confidence_label,
            ),
            active_signals=[
                ActiveSignalOut(
                    id=s.id,
                    pair=s.pair,
                    side=s.side,
                    entry=s.entry,
                    target=s.target,
                    position=s.position,
                )
                for s in signals
            ],
            win_rate=WinRateOut(
                percent=portfolio.win_rate_percent,
                period=portfolio.win_rate_period,
                win_streak=portfolio.win_streak,
                profit_factor=portfolio.profit_factor,
            ),
            open_positions=[OpenPositionOut.model_validate(p) for p in positions],
            watchlist=[
                WatchlistItemOut(
                    id=w.id,
                    symbol=w.symbol,
                    price=w.price,
                    change_percent=w.change_percent,
                )
                for w in watchlist
            ],
            recent_activity=[
                ActivityEventOut(
                    id=a.id,
                    type=a.event_type,
                    message=a.message,
                    timestamp=a.time_label,
                )
                for a in activity
            ],
            latest_ai_analyses=[AiAnalysisSummaryOut.model_validate(x) for x in analyses],
        )

    async def get_overview(self, user_id: UUID) -> PortfolioOverviewOut:
        portfolio = await self.repo.get_by_user_id(user_id)
        if portfolio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        holdings = await self.repo.list_holdings(portfolio.id)
        slices = await self.repo.list_allocation_slices(user_id)
        monthly = await self.repo.list_monthly_returns(user_id)
        health = await self.repo.list_health_metrics(user_id)
        recommendations = await self.repo.list_recommendations(user_id)
        timeline = await self.repo.list_timeline(user_id)

        allocation: dict[str, list[AllocationSliceOut]] = {}
        for s in slices:
            allocation.setdefault(s.view, []).append(
                AllocationSliceOut(id=s.slice_key, label=s.label, percent=s.percent, color=s.color)
            )

        metrics = [
            PortfolioMetricOut(
                id="balance",
                label="TOTAL BALANCE",
                value=f"${portfolio.total_balance:,.2f}",
                meta=f"{portfolio.change_24h_percent:+.1f}% (24h)",
                tone="success" if portfolio.change_24h_percent >= 0 else "danger",
                icon="wallet",
            ),
            PortfolioMetricOut(
                id="unrealized",
                label="UNREALIZED PNL",
                value=_fmt_money(portfolio.unrealized_pnl),
                meta=f"Equity: ${portfolio.equity:,.2f}",
                tone="success" if portfolio.unrealized_pnl >= 0 else "danger",
                icon="chart",
            ),
            PortfolioMetricOut(
                id="realized",
                label="REALIZED PNL (YTD)",
                value=f"${portfolio.realized_pnl_ytd:,.2f}",
                meta=f"Win Rate: {portfolio.win_rate_percent}%",
                tone="default",
                icon="check",
            ),
        ]

        return PortfolioOverviewOut(
            metrics=metrics,
            holdings=[
                HoldingOut(
                    id=h.id,
                    symbol=h.symbol,
                    name=h.name,
                    exchange=h.exchange,
                    quantity=h.quantity,
                    quantity_label=_quantity_label(h.quantity),
                    price=h.price,
                    value=h.value,
                    pnl=h.pnl,
                    allocation=h.allocation,
                    avg_entry=h.avg_entry,
                    realized_pnl=h.realized_pnl,
                    pinned=h.pinned,
                )
                for h in holdings
            ],
            allocation=allocation,
            monthly_returns=[
                MonthlyReturnOut(id=m.period_key, label=m.label, value=m.value) for m in monthly
            ],
            health_metrics=[
                PortfolioHealthMetricOut(id=h.metric_key, label=h.label, value=h.value, tone=h.tone)
                for h in health
            ],
            ai_score=AiPortfolioScoreOut(
                overall=portfolio.ai_score_overall,
                risk=portfolio.ai_score_risk,
                diversification=portfolio.ai_score_diversification,
                liquidity=portfolio.ai_score_liquidity,
                volatility=portfolio.ai_score_volatility,
                capital_allocation=portfolio.ai_score_capital_allocation,
                recommendation=portfolio.ai_score_recommendation,
            ),
            recommendations=[AiRecommendationOut.model_validate(r) for r in recommendations],
            timeline=[
                PortfolioTimelineEventOut(
                    id=t.id,
                    time=t.time_label,
                    kind=t.kind,
                    title=t.title,
                    detail=t.detail,
                )
                for t in timeline
            ],
        )

    async def get_performance(self, user_id: UUID, range_key: str) -> PerformanceSeriesOut:
        if range_key not in ALLOWED_RANGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid range. Allowed: {sorted(ALLOWED_RANGES)}",
            )

        portfolio = await self.repo.get_by_user_id(user_id)
        if portfolio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        points = await self.repo.list_performance_points(user_id, range_key)
        series: dict[str, list[PortfolioPointOut]] = {k: [] for k in ALLOWED_SERIES}
        for p in points:
            if p.series_kind in series:
                series[p.series_kind].append(PortfolioPointOut(time=p.time, value=p.value))

        return PerformanceSeriesOut(range=range_key, series=series)

    async def get_holding_detail(self, user_id: UUID, holding_id: UUID) -> AssetDetailOut:
        portfolio = await self.repo.get_by_user_id(user_id)
        if portfolio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        holding = await self.repo.get_holding(portfolio.id, holding_id)
        if holding is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")

        return AssetDetailOut(
            overview=holding.overview,
            ai_analysis=holding.ai_analysis,
            risk_assessment=holding.risk_assessment,
            suggested_actions=list(holding.suggested_actions or []),
            trade_history=list(holding.trade_history or []),
        )
