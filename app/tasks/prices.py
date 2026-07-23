from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from app.core.redis_client import CHANNEL_PRICES, publish_json
from app.tasks.celery_app import celery_app

FALLBACK = {
    "BTCUSDT": 65000.0,
    "ETHUSDT": 3400.0,
    "SOLUSDT": 145.0,
    "LINKUSDT": 14.5,
}


@celery_app.task(name="app.tasks.prices.publish_price_ticks")
def publish_price_ticks() -> dict:
    ticks = []
    now = datetime.now(timezone.utc).isoformat()
    for symbol, base in FALLBACK.items():
        price = round(base * (1 + random.uniform(-0.0015, 0.0015)), 4)
        ticks.append({"symbol": symbol, "price": price, "ts": now})
    event = {"type": "price.tick", "ticks": ticks, "ts": now}
    publish_json(CHANNEL_PRICES, json.dumps(event))
    return {"published": len(ticks)}
