from __future__ import annotations

import uuid
from typing import Any

from app.exchange.base import ExchangeAdapter, OrderRequest, OrderResult


class SimulatedExchangeAdapter(ExchangeAdapter):
    name = "simulated"

    def __init__(self, balances: dict[str, Any] | None = None) -> None:
        self._balances = balances or {
            "USDT": {"free": 10000.0, "locked": 0.0},
            "BTC": {"free": 0.15, "locked": 0.0},
            "ETH": {"free": 2.5, "locked": 0.0},
        }

    async def get_balances(self) -> dict[str, Any]:
        return {"assets": self._balances, "source": self.name}

    async def place_order(self, order: OrderRequest) -> OrderResult:
        oid = f"sim-{uuid.uuid4().hex[:12]}"
        return OrderResult(
            order_id=oid,
            status="filled" if order.order_type == "market" else "accepted",
            symbol=order.symbol.upper(),
            side=order.side.lower(),
            quantity=order.quantity,
            detail={"simulated": True, "order_type": order.order_type, "price": order.price},
        )

    async def ping(self) -> bool:
        return True
