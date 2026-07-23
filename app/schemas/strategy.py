from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrategyNodeOut(BaseModel):
    id: str
    category: str
    type_id: str
    title: str
    description: str | None = None
    lines: list[str] | None = None
    collapsed: bool = False
    validation: str = "idle"
    config: dict[str, Any] | None = None
    ports: list[dict[str, Any]] | None = None


class StrategyEdgeOut(BaseModel):
    id: str
    source: str
    target: str
    source_port: str | None = None
    target_port: str | None = None
    label: str | None = None
    highlighted: bool = False
    errored: bool = False


class StrategyCanvasOut(BaseModel):
    strategy_id: UUID
    nodes: list[StrategyNodeOut] = Field(default_factory=list)
    edges: list[StrategyEdgeOut] = Field(default_factory=list)


class StrategyValidationIssueOut(BaseModel):
    code: str
    label: str
    tone: str


class BacktestMetricsOut(BaseModel):
    win_rate: Decimal
    profit_factor: Decimal
    drawdown: Decimal
    sharpe: Decimal
    trades: int
    monthly_return: str


class BacktestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    strategy_id: UUID
    status: str
    symbol: str
    timeframe: str
    range_label: str
    win_rate: Decimal
    profit_factor: Decimal
    drawdown: Decimal
    sharpe: Decimal
    trades: int
    monthly_return: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class StrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    symbol: str
    timeframe: str
    status: str
    win_rate: Decimal
    profit_factor: Decimal
    drawdown: Decimal
    last_backtest: str
    description: str
    markets: list[str]
    timeframes: list[str]
    version: str
    created_at: datetime
    updated_at: datetime
    created_at_label: str
    updated_at_label: str
    ai_confidence: int
    estimated_risk: str
    estimated_monthly_return: str
    max_drawdown: Decimal
    exchange: str
    strategy_type: str
    tags: list[str]
    author: str


class StrategyDetailOut(StrategyOut):
    canvas: StrategyCanvasOut
    validation: list[StrategyValidationIssueOut] = Field(default_factory=list)
    latest_backtest: BacktestRunOut | None = None


class StrategyListOut(BaseModel):
    items: list[StrategyOut]
    total: int
    page: int
    page_size: int


class CreateStrategyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    symbol: str = Field(default="BTC/USDT", max_length=32)
    timeframe: str = Field(default="15m", max_length=8)
    description: str = ""
    strategy_type: str = Field(default="Momentum", max_length=64)
    exchange: str = Field(default="Binance", max_length=64)
    estimated_risk: str = Field(default="medium", pattern="^(low|medium|high)$")
    tags: list[str] = Field(default_factory=list)
    status: str = Field(default="draft", pattern="^(active|paused|draft|archived)$")


class UpdateStrategyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    symbol: str | None = None
    timeframe: str | None = None
    description: str | None = None
    strategy_type: str | None = None
    exchange: str | None = None
    estimated_risk: str | None = Field(default=None, pattern="^(low|medium|high)$")
    tags: list[str] | None = None
    status: str | None = Field(default=None, pattern="^(active|paused|draft|archived)$")
    markets: list[str] | None = None
    timeframes: list[str] | None = None


class StrategyNodeIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    category: str
    type_id: str
    title: str
    description: str | None = None
    lines: list[str] | None = None
    collapsed: bool = False
    validation: str = "idle"
    config: dict[str, Any] | None = None
    ports: list[dict[str, Any]] | None = None


class StrategyEdgeIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    source: str
    target: str
    source_port: str | None = None
    target_port: str | None = None
    label: str | None = None
    highlighted: bool = False
    errored: bool = False


class SaveCanvasRequest(BaseModel):
    nodes: list[StrategyNodeIn] = Field(default_factory=list)
    edges: list[StrategyEdgeIn] = Field(default_factory=list)


class GenerateStrategyRequest(BaseModel):
    prompt: str = Field(..., min_length=8, max_length=2000)


class GenerateStrategyOut(BaseModel):
    strategy: StrategyDetailOut
    pipeline_steps: list[dict[str, str]]


class RunBacktestRequest(BaseModel):
    range_label: str = Field(default="90d", max_length=32)
    symbol: str | None = None
    timeframe: str | None = None


class AiAssistRequest(BaseModel):
    action: str = Field(
        ...,
        pattern="^(generate|optimize|explain|weaknesses|risk|indicators|convert)$",
    )
    prompt: str | None = Field(default=None, max_length=2000)


class AiAssistOut(BaseModel):
    action: str
    title: str
    detail: str
    suggestions: list[str] = Field(default_factory=list)


class StrategiesWorkspaceOut(BaseModel):
    page_meta: dict[str, str]
    filter_options: dict[str, list[dict[str, str]]]
    ai_assistant_actions: list[dict[str, str]]
    builder_toolbar: list[dict[str, str]]
    card_actions: list[dict[str, str]]
    generate_pipeline_steps: list[dict[str, str]]
    generate_prompt_examples: list[str]
    backtest_defaults: BacktestMetricsOut
