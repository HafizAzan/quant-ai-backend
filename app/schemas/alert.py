from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateAlertRequest(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=32)
    title: str | None = Field(default=None, max_length=255)
    category: str = Field(default="price", max_length=32)
    priority: str = Field(default="high", pattern="^(critical|high|medium|low)$")
    frequency: str = Field(default="recurring", pattern="^(recurring|one_time)$")
    channels: list[str] = Field(default_factory=lambda: ["push"])
    operator: str = Field(default="above", pattern="^(above|below|cross)$")
    target_price: Decimal = Field(..., gt=0)
    entry: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    source_analysis_id: UUID | None = None


class SnoozeRequest(BaseModel):
    minutes: int = Field(default=60, ge=5, le=10080)


class AlertConditionOut(BaseModel):
    id: UUID
    condition_type: str
    operator: str
    target_value: Decimal
    logic: str


class AlertExplanationOut(BaseModel):
    why_triggered: str = ""
    market_structure: str = ""
    supporting_indicators: list[str] = Field(default_factory=list)
    confidence: int = 0
    suggested_action: str = ""
    risk_level: str = ""
    probability: str = ""
    related_assets: list[str] = Field(default_factory=list)


class AlertTimelineOut(BaseModel):
    id: UUID
    kind: str
    time: str
    detail: str


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    title: str
    category: str
    priority: str
    frequency: str
    channels: list[str]
    enabled: bool
    status: str
    age: str
    last_triggered: str
    entry: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    conditions: list[AlertConditionOut] = Field(default_factory=list)
    explanation: AlertExplanationOut
    timeline: list[AlertTimelineOut] = Field(default_factory=list)
    created_at: datetime


class AlertMetricOut(BaseModel):
    id: str
    label: str
    value: str
    meta: str
    tone: str = "default"


class MonitoringWidgetOut(BaseModel):
    id: str
    label: str
    value: str
    tone: str = "default"


class NotificationChannelOut(BaseModel):
    id: UUID
    kind: str
    label: str
    status: str
    last_delivery: str
    success_rate: str
    latency: str


class AlertHistoryOut(BaseModel):
    id: UUID
    time: str
    badge: str
    badge_tone: str
    detail: str


class AlertAnalyticsOut(BaseModel):
    id: str
    label: str
    value: str
    tone: str = "default"


class AiWatchItemOut(BaseModel):
    id: UUID
    symbol: str
    status: str
    confidence: int | None = None
    tone: str = "default"


class TriggerSeriesPointOut(BaseModel):
    time: int
    value: int


class AlertsDeskOut(BaseModel):
    metrics: list[AlertMetricOut]
    monitoring: list[MonitoringWidgetOut]
    channels: list[NotificationChannelOut]
    history: list[AlertHistoryOut]
    analytics: list[AlertAnalyticsOut]
    watchlist: list[AiWatchItemOut]
    trigger_series: list[TriggerSeriesPointOut]
    rule_conditions: list[dict[str, str]]


class AlertsListOut(BaseModel):
    items: list[AlertOut]
    total: int
    page: int
    page_size: int


class EvaluateAlertsOut(BaseModel):
    checked: int
    triggered: int
    triggers: list[AlertHistoryOut]


class ChannelTestOut(BaseModel):
    channel_id: UUID
    status: str
    message: str
