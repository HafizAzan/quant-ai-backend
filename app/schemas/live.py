from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LiveBalanceOut(BaseModel):
    id: UUID
    asset: str
    amount: str
    change_24h: Decimal


class LivePositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    side: str
    size: str
    entry: Decimal
    mark: Decimal
    leverage: int
    unrealized_pnl: Decimal
    health: str
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None


class LiveOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    type_label: str
    side: str
    price: Decimal
    amount: str
    filled_percent: Decimal


class LiveActivityOut(BaseModel):
    id: UUID
    timestamp: str
    title: str
    detail: str
    category: str
    severity: str


class GuardianAlertOut(BaseModel):
    id: UUID
    title: str
    detail: str
    severity: str
    action_label: str | None = None


class LiveDeskOut(BaseModel):
    page_meta: dict[str, str]
    exchange: str
    api_active: bool
    auto_trading: bool
    trading_locked: bool
    risk_only_mode: bool
    default_leverage: int
    margin_type: str
    total_unrealized_pnl: Decimal
    risk_controls: dict[str, Any]
    balances: list[LiveBalanceOut]
    portfolio_exposure: dict[str, Any]
    positions: list[LivePositionOut]
    orders: list[LiveOrderOut]
    activity: list[LiveActivityOut]
    guardian_alerts: list[GuardianAlertOut]
    market_monitor: list[dict[str, Any]]
    system_status: list[dict[str, Any]]
    emergency_actions: list[dict[str, str]]
    bottom_bar_primary: list[dict[str, str]]
    bottom_bar_tools: list[dict[str, str]]
    ai_assistant_prompts: list[dict[str, str]]
    ai_approval_defaults: dict[str, Any]


class PositionDetailOut(BaseModel):
    position: LivePositionOut
    timeline: list[dict[str, str]]
    ai_analysis: str
    entry_reason: str
    current_risk: str
    stop_loss_history: list[dict[str, str]]
    take_profit_history: list[dict[str, str]]
    ai_suggestions: list[str]
    trade_events: list[dict[str, str]]
    market_snapshot: str


class SetAutoTradingRequest(BaseModel):
    enabled: bool


class LiveSettingsRequest(BaseModel):
    leverage: int | None = Field(default=None, ge=1, le=125)
    margin_type: str | None = Field(default=None, pattern="^(cross|isolated)$")


class PlaceLiveOrderRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT", min_length=3, max_length=32)
    side: str = Field(..., pattern="^(long|short)$")
    order_type: str = Field(default="market", pattern="^(market|limit|stop)$")
    amount: Decimal = Field(..., gt=0)
    price: Decimal | None = None
    leverage: int | None = Field(default=None, ge=1, le=125)
    margin_type: str | None = Field(default=None, pattern="^(cross|isolated)$")
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    confirm: bool = False


class AiApprovalCheckOut(BaseModel):
    id: str
    label: str
    status: str
    value: str


class TradePreviewOut(BaseModel):
    approval: dict[str, Any]
    confirm: dict[str, Any]


class PlaceLiveOrderOut(BaseModel):
    message: str
    order: LiveOrderOut | None = None
    position: LivePositionOut | None = None
    desk: LiveDeskOut | None = None


class PositionActionRequest(BaseModel):
    action: str = Field(..., pattern="^(close|reverse|partial|breakeven|trail)$")
    percent: Decimal | None = Field(default=None, gt=0, le=100)


class EmergencyStopRequest(BaseModel):
    action: str = Field(..., pattern="^(close_all|cancel_all|disable_auto|lock|risk_only)$")


class EmergencyStopOut(BaseModel):
    message: str
    action: str
    result: dict[str, Any]
    desk: LiveDeskOut


class AskAiRequest(BaseModel):
    prompt_id: str = Field(..., max_length=32)


class AskAiOut(BaseModel):
    prompt_id: str
    reply: str


class EmergencyEventOut(BaseModel):
    id: UUID
    action: str
    detail: str
    result: dict[str, Any]
    created_at: datetime
