from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MarketAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    symbol: str
    trading_pair: str
    name: str
    category: str
    rank: int
    price: Decimal
    change_24h: Decimal
    volume_24h: Decimal
    market_cap: Decimal
    ai_signal: str
    color: str
    is_high_volume: bool
    is_new_listing: bool
    is_crypto_ai: bool
    favorite: bool = False
    pair_label: str | None = None


class MarketsListData(BaseModel):
    items: list[MarketAssetOut]
    page: int
    page_size: int
    total: int
    total_pages: int
    from_index: int
    to_index: int


class MarketSentimentOut(BaseModel):
    title: str = "Fear & Greed"
    score: int
    zone: str
    description: str


class MarketDominanceOut(BaseModel):
    btc_percent: Decimal
    alts_percent: Decimal
    stables_percent: Decimal


class MarketAiPickOut(BaseModel):
    name: str
    symbol: str
    confidence: Decimal
    action_label: str = "View Detailed Analysis"


class MarketsMetaOut(BaseModel):
    sentiment: MarketSentimentOut
    dominance: MarketDominanceOut
    ai_pick: MarketAiPickOut | None = None


class CandleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    time: int = Field(description="Unix seconds open time")
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class CandlesData(BaseModel):
    symbol: str
    timeframe: str
    candles: list[CandleOut]


class FavoriteToggleOut(BaseModel):
    asset_id: UUID
    favorite: bool
