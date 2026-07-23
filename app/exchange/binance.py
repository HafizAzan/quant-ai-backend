from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from typing import Any
from urllib.parse import urlencode

import httpx

from app.exchange.base import ExchangeAdapter, OrderRequest, OrderResult


class BinanceExchangeAdapter(ExchangeAdapter):
    """REST adapter for Binance spot (testnet or main). Falls back gracefully on errors."""

    name = "binance"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        testnet: bool = True,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.timeout = timeout
        self.base_url = (
            "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        )

    def _sign(self, params: dict[str, Any]) -> str:
        query = urlencode(params)
        return hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()

    async def ping(self) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/api/v3/ping")
            return r.status_code == 200

    async def get_balances(self) -> dict[str, Any]:
        params: dict[str, Any] = {"timestamp": int(time.time() * 1000)}
        params["signature"] = self._sign(params)
        headers = {"X-MBX-APIKEY": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/api/v3/account", params=params, headers=headers)
            if r.status_code != 200:
                raise RuntimeError(f"Binance account error: {r.status_code} {r.text[:200]}")
            data = r.json()
            assets = {
                b["asset"]: {"free": float(b["free"]), "locked": float(b["locked"])}
                for b in data.get("balances", [])
                if float(b["free"]) > 0 or float(b["locked"]) > 0
            }
            return {"assets": assets, "source": self.name, "can_trade": data.get("canTrade")}

    async def place_order(self, order: OrderRequest) -> OrderResult:
        params: dict[str, Any] = {
            "symbol": order.symbol.upper().replace("/", ""),
            "side": order.side.upper(),
            "type": order.order_type.upper(),
            "quantity": order.quantity,
            "timestamp": int(time.time() * 1000),
        }
        if order.order_type == "limit":
            if order.price is None:
                raise ValueError("Limit order requires price")
            params["price"] = order.price
            params["timeInForce"] = "GTC"
        params["signature"] = self._sign(params)
        headers = {"X-MBX-APIKEY": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/api/v3/order", params=params, headers=headers)
            if r.status_code != 200:
                # Dev-safe: return rejected result instead of crashing the API
                return OrderResult(
                    order_id=f"rej-{uuid.uuid4().hex[:10]}",
                    status="rejected",
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    detail={"error": r.text[:300], "status_code": r.status_code},
                )
            data = r.json()
            return OrderResult(
                order_id=str(data.get("orderId", uuid.uuid4().hex)),
                status=str(data.get("status", "NEW")).lower(),
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                detail=data,
            )
