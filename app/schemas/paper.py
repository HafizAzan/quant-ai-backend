from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaperMetricOut(BaseModel):
    id: str
    label: str
    value: str
    meta: str
    tone: str = "default"
    progress: float | None = None


class EquityPointOut(BaseModel):
    label: str
    value: Decimal


class PaperPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    side: str
    size: Decimal
    size_label: str
    entry: Decimal
    current: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    unrealized_pnl: Decimal
    health: str
    lifecycle: str
    opened_at: str
    notes: str | None = None


class PendingOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    side: str
    type: str
    size_label: str
    limit_price: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    created_at: str


class TradeHistoryOut(BaseModel):
    id: UUID
    symbol: str
    side: str
    size_label: str
    entry: Decimal
    exit: Decimal
    pnl: Decimal
    closed_at: str
    lifecycle: str


class SentinelSuggestionOut(BaseModel):
    id: UUID
    message: str
    symbol: str
    suggested_tp: Decimal | None = None


class PaperDeskOut(BaseModel):
    learning_mode: str
    metrics: list[PaperMetricOut]
    open_positions: list[PaperPositionOut]
    pending_orders: list[PendingOrderOut]
    trade_history: list[TradeHistoryOut]
    sentinel: SentinelSuggestionOut | None = None
    symbols: list[dict[str, str]]


class EquityCurveOut(BaseModel):
    range: str
    points: list[EquityPointOut]


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=32)
    side: str = Field(..., pattern="^(long|short)$")
    order_type: str = Field(..., pattern="^(market|limit)$")
    size: Decimal = Field(..., gt=0)
    size_mode: str = Field(default="fixed", pattern="^(fixed|percent|risk|ai)$")
    limit_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    use_ai_sl_tp: bool = False


class TradePreviewOut(BaseModel):
    symbol: str
    side: str
    entry_price: Decimal
    position_size: str
    quantity: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    risk_percent: Decimal
    risk_reward: str
    estimated_fees: str
    ai_confidence: int
    holding_time: str
    explanations: list[dict[str, str]]
    warnings: list[dict[str, str]]
    risk_level: str


class PlaceOrderOut(BaseModel):
    order_id: UUID
    status: str
    position_id: UUID | None = None
    message: str


class SetLearningModeRequest(BaseModel):
    mode: str = Field(..., pattern="^(practice|learning|exam)$")


class AskAiRequest(BaseModel):
    prompt_id: str = Field(..., pattern="^(losing|tp|avoid|entry|sl)$")
    position_id: UUID | None = None


class AskAiOut(BaseModel):
    prompt_id: str
    answer: str
    exam_score: int | None = None
    exam_summary: str | None = None


class TimelineEventOut(BaseModel):
    id: UUID
    time: str
    title: str
    detail: str


class PositionDetailOut(BaseModel):
    position: PaperPositionOut
    timeline: list[TimelineEventOut]
    risk_changes: list[dict[str, str]]
    trade_events: list[dict[str, str]]
    execution_history: list[dict[str, str]]
    ai_analysis: str
    future_commentary: str
    chart_snapshot_label: str


class SentinelActionRequest(BaseModel):
    action: str = Field(..., pattern="^(apply|ignore)$")
