from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExchangeAccountOut(BaseModel):
    id: UUID
    exchange: str
    label: str
    key_prefix: str
    permissions: str
    is_active: bool
    is_testnet: bool
    last_sync_at: datetime | None = None
    last_sync_status: str
    last_sync_error: str | None = None
    balances_cache: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ExchangeConnectRequest(BaseModel):
    exchange: str = Field(default="binance", max_length=64)
    label: str = Field(default="Primary", max_length=120)
    api_key: str = Field(..., min_length=8, max_length=256)
    api_secret: str = Field(..., min_length=8, max_length=256)
    permissions: str = Field(default="trade", pattern="^(read|trade)$")
    is_testnet: bool = True


class ExchangeSyncOut(BaseModel):
    account: ExchangeAccountOut | None = None
    balances: dict[str, Any]
    source: str  # simulated|binance|cache


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=3, max_length=32)
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)
    order_type: str = Field(default="market", pattern="^(market|limit)$")
    price: float | None = Field(default=None, gt=0)


class PlaceOrderOut(BaseModel):
    order_id: str
    status: str
    symbol: str
    side: str
    quantity: float
    source: str
    detail: dict[str, Any] = Field(default_factory=dict)
