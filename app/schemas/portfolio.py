from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ----- Dashboard -----


class PortfolioBalanceOut(BaseModel):
    title: str = "Total Portfolio Balance"
    amount: Decimal
    percentage: Decimal
    percentage_label: str = "MTD"
    last_updated: str = "1m ago"
    chart_data: list[float] = Field(default_factory=list)


class PnlPerformanceOut(BaseModel):
    title: str = "PnL Performance"
    daily_pnl: Decimal
    weekly_pnl: Decimal
    weekly_target_percent: Decimal


class AiConfidenceOut(BaseModel):
    title: str = "AI Confidence"
    percent: Decimal
    label: str


class ActiveSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pair: str
    side: str
    entry: str
    target: str
    position: str


class WinRateOut(BaseModel):
    title: str = "Win Rate"
    percent: Decimal
    period: str
    win_streak: str
    profit_factor: Decimal


class OpenPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset: str
    side: str
    leverage: str
    size: str
    entry: Decimal
    mark: Decimal
    pnl: Decimal
    pnl_percent: Decimal


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    price: Decimal
    change_percent: Decimal


class ActivityEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    message: str
    timestamp: str


class AiAnalysisSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticker: str
    status: str
    summary: str
    confidence: int


class DashboardSnapshotOut(BaseModel):
    portfolio_balance: PortfolioBalanceOut
    pnl_performance: PnlPerformanceOut
    ai_confidence: AiConfidenceOut
    active_signals: list[ActiveSignalOut]
    win_rate: WinRateOut
    open_positions: list[OpenPositionOut]
    watchlist: list[WatchlistItemOut]
    recent_activity: list[ActivityEventOut]
    latest_ai_analyses: list[AiAnalysisSummaryOut]


# ----- Portfolio -----


class PortfolioMetricOut(BaseModel):
    id: str
    label: str
    value: str
    meta: str
    tone: str = "default"
    icon: str


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    name: str
    exchange: str
    quantity: Decimal
    quantity_label: str
    price: Decimal
    value: Decimal
    pnl: Decimal
    allocation: Decimal
    avg_entry: Decimal
    realized_pnl: Decimal
    pinned: bool = False


class AllocationSliceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    percent: Decimal
    color: str


class MonthlyReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    value: Decimal | None


class PortfolioHealthMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    value: str
    tone: str = "default"


class AiPortfolioScoreOut(BaseModel):
    overall: int
    risk: str
    diversification: str
    liquidity: str
    volatility: str
    capital_allocation: str
    recommendation: str


class AiRecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    detail: str
    severity: str


class PortfolioTimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    time: str
    kind: str
    title: str
    detail: str


class AssetDetailOut(BaseModel):
    overview: str
    ai_analysis: str
    risk_assessment: str
    suggested_actions: list[str]
    trade_history: list[dict]


class PortfolioPointOut(BaseModel):
    time: int
    value: Decimal


class PortfolioOverviewOut(BaseModel):
    metrics: list[PortfolioMetricOut]
    holdings: list[HoldingOut]
    allocation: dict[str, list[AllocationSliceOut]]
    monthly_returns: list[MonthlyReturnOut]
    health_metrics: list[PortfolioHealthMetricOut]
    ai_score: AiPortfolioScoreOut
    recommendations: list[AiRecommendationOut]
    timeline: list[PortfolioTimelineEventOut]


class PerformanceSeriesOut(BaseModel):
    range: str
    series: dict[str, list[PortfolioPointOut]]
