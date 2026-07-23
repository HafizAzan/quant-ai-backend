from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TradeScoreOut(BaseModel):
    overall: int = 0
    entry_quality: int = 0
    exit_quality: int = 0
    risk_management: int = 0
    psychology: int = 0
    execution: int = 0
    patience: int = 0
    rule_compliance: int = 0
    grade: str = "C"


class TradeImprovementOut(BaseModel):
    went_well: list[str] = Field(default_factory=list)
    went_wrong: list[str] = Field(default_factory=list)
    should_improve: list[str] = Field(default_factory=list)
    alternative_entry: str | None = None
    alternative_exit: str | None = None
    better_stop_loss: str | None = None
    better_take_profit: str | None = None
    professional_tips: list[str] = Field(default_factory=list)
    next_focus: str = ""


class JournalTimelineOut(BaseModel):
    id: UUID
    kind: str
    time: str
    title: str
    detail: str


class JournalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date_group: str
    symbol: str
    side: str
    strategy_tag: str
    emotion_tag: str | None = None
    timeframe: str
    market_condition: str
    outcome: str
    pnl: Decimal
    roi_percent: Decimal
    risk_reward: str
    duration: str
    exited_at: str
    entry_price: Decimal
    exit_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    notes: str
    psychology_notes: str
    ai_summary: str
    score: TradeScoreOut
    mistakes: list[str]
    improvement: TradeImprovementOut
    timeline: list[JournalTimelineOut]
    candles: list[dict[str, Any]]
    entry_time: int
    exit_time: int
    traded_at: datetime


class JournalGroupOut(BaseModel):
    date: str
    items: list[JournalEntryOut]


class JournalListOut(BaseModel):
    items: list[JournalEntryOut]
    grouped: list[JournalGroupOut]
    total: int
    page: int
    page_size: int


class CreateJournalEntryRequest(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=32)
    side: str = Field(..., pattern="^(long|short)$")
    strategy_tag: str = Field(default="SCALPING", max_length=32)
    emotion_tag: str | None = Field(default=None, max_length=32)
    timeframe: str = Field(default="1h", max_length=8)
    market_condition: str = Field(default="", max_length=64)
    outcome: str = Field(default="breakeven", pattern="^(win|loss|breakeven)$")
    pnl: Decimal = Decimal("0")
    roi_percent: Decimal = Decimal("0")
    risk_reward: str = "1:1"
    duration: str = ""
    exited_at: str = ""
    entry_price: Decimal
    exit_price: Decimal
    stop_loss: Decimal = Decimal("0")
    take_profit: Decimal = Decimal("0")
    notes: str = ""
    psychology_notes: str = ""
    paper_position_id: UUID | None = None
    mistakes: list[str] = Field(default_factory=list)


class UpdateJournalEntryRequest(BaseModel):
    notes: str | None = None
    psychology_notes: str | None = None
    emotion_tag: str | None = None
    strategy_tag: str | None = None
    outcome: str | None = Field(default=None, pattern="^(win|loss|breakeven)$")
    mistakes: list[str] | None = None


class TraderEvolutionOut(BaseModel):
    level: str
    overall_score: int
    discipline: int
    psychology: int
    risk_management: int
    execution: int
    biggest_weakness: str
    current_mission: str
    estimated_improvement: str


class AiCoachItemOut(BaseModel):
    id: UUID
    title: str
    detail: str
    action_label: str | None = None


class JournalDeskOut(BaseModel):
    evolution: TraderEvolutionOut
    analytics: dict[str, str]
    patterns: list[dict[str, Any]]
    allocation: list[dict[str, Any]]
    monthly_progress: list[dict[str, Any]]
    daily_pnl: list[dict[str, Any]]
    coach: list[AiCoachItemOut]
    strategy_insight: dict[str, str]
    filter_options: dict[str, list[dict[str, str]]]
    mistake_labels: dict[str, str]
