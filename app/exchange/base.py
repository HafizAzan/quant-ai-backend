from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    price: float | None = None


@dataclass
class OrderResult:
    order_id: str
    status: str
    symbol: str
    side: str
    quantity: float
    detail: dict[str, Any] = field(default_factory=dict)


class ExchangeAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def get_balances(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResult:
        raise NotImplementedError

    @abstractmethod
    async def ping(self) -> bool:
        raise NotImplementedError
