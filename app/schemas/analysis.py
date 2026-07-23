from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerateAnalysisRequest(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=32)
    timeframe: str = Field(default="1h", pattern="^(1m|5m|15m|1h|4h|1d|1w)$")
    lookback: int = Field(default=200, ge=20, le=1000)
    save: bool = False


class PriceLineOverlayOut(BaseModel):
    id: str
    kind: str
    price: float
    title: str | None = None
    color: str | None = None


class ZoneOverlayOut(BaseModel):
    id: str
    kind: str
    from_: float = Field(alias="from")
    to: float
    label: str | None = None
    color: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class MarkerOverlayOut(BaseModel):
    id: str
    time: int
    position: str
    shape: str
    color: str | None = None
    text: str | None = None


class ChartOverlaysOut(BaseModel):
    price_lines: list[PriceLineOverlayOut] = Field(default_factory=list)
    zones: list[ZoneOverlayOut] = Field(default_factory=list)
    markers: list[MarkerOverlayOut] = Field(default_factory=list)
    annotations: list[dict[str, Any]] = Field(default_factory=list)


class SupplyDemandOut(BaseModel):
    label: str
    range: str
    strength: int


class AiSignalPanelOut(BaseModel):
    title: str = "AI Signal Analysis"
    badge: str
    trend: dict[str, str]
    market_structure: dict[str, str]
    supply_demand: dict[str, SupplyDemandOut]
    risk_reward: dict[str, str | int]
    reasoning: dict[str, str]


class TradeMetricsOut(BaseModel):
    entry: str
    stop_loss: str
    take_profit: str
    entry_raw: Decimal
    stop_loss_raw: Decimal
    take_profit_raw: Decimal


class WorkspaceMetaOut(BaseModel):
    pair: str
    symbol: str
    timeframe: str
    exchange: str
    open: str
    high: str
    low: str
    close: str
    change_percent: Decimal
    volume: str
    ai_zones: str


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    timeframe: str
    exchange: str
    model: str
    lookback: int
    trend: str
    structure: str
    confidence: int
    is_saved: bool
    entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    risk_reward_ratio: str
    created_at: datetime
    meta: WorkspaceMetaOut
    trade_metrics: TradeMetricsOut
    signal: AiSignalPanelOut
    overlays: dict[str, Any]


class AnalysisListItemOut(BaseModel):
    id: UUID
    symbol: str
    timeframe: str
    trend: str
    confidence: int
    is_saved: bool
    entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    created_at: datetime


class AnalysisListOut(BaseModel):
    items: list[AnalysisListItemOut]
    total: int


class WorkspaceOut(BaseModel):
    symbols: list[dict[str, str]]
    timeframes: list[dict[str, str]]
    layouts: list[dict[str, str]]
    analysis: AnalysisOut | None
    candles: list[dict[str, float | int]]


class AlertDraftOut(BaseModel):
    symbol: str
    conditions: list[dict[str, str | float]]
    source_analysis_id: UUID
    message: str
