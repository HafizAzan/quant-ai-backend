"""Seed a sample saved AI analysis for users.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_analysis
  .venv\\Scripts\\python -m app.scripts.seed_analysis --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.analysis import AiAnalysis
from app.models.user import User


def _d(v: str | float | int) -> Decimal:
    return Decimal(str(v))


async def seed_for_user(session, user_id: UUID) -> None:
    existing = await session.execute(
        select(AiAnalysis).where(
            AiAnalysis.user_id == user_id,
            AiAnalysis.symbol == "BTCUSDT",
            AiAnalysis.timeframe == "1h",
            AiAnalysis.is_saved.is_(True),
        )
    )
    if existing.scalar_one_or_none() is not None:
        return

    overlays = {
        "priceLines": [
            {"id": "resistance", "kind": "resistance", "price": 70500, "title": "RESISTANCE", "color": "#b91a24"},
            {"id": "support", "kind": "support", "price": 68000, "title": "SUPPORT", "color": "#22c55e"},
            {"id": "tp2", "kind": "take_profit", "price": 71200, "title": "TP2", "color": "#adc6ff"},
            {"id": "tp1", "kind": "take_profit", "price": 69800, "title": "TP1", "color": "#5b8def"},
            {"id": "entry", "kind": "entry", "price": 68400, "title": "ENTRY", "color": "#5b8def"},
            {"id": "sl", "kind": "stop_loss", "price": 67100, "title": "SL", "color": "#b91a24"},
        ],
        "zones": [
            {
                "id": "supply-1",
                "kind": "supply",
                "from": 71200,
                "to": 71850,
                "label": "Supply",
                "color": "#b91a24",
            },
            {
                "id": "demand-1",
                "kind": "demand",
                "from": 67400,
                "to": 68100,
                "label": "Demand",
                "color": "#22c55e",
            },
        ],
        "markers": [
            {
                "id": "choch-1",
                "time": 1719741600,
                "position": "belowBar",
                "shape": "arrowUp",
                "color": "#adc6ff",
                "text": "CHoCH",
            }
        ],
        "annotations": [],
    }

    session.add(
        AiAnalysis(
            user_id=user_id,
            symbol="BTCUSDT",
            timeframe="1h",
            exchange="Binance",
            model="PRO MODEL",
            lookback=200,
            open_price=_d("67980"),
            high_price=_d("68910"),
            low_price=_d("67640"),
            close_price=_d("68432.12"),
            change_percent=_d("2.45"),
            volume_label="1.84B",
            ai_zones_label="Supply / Demand Active",
            trend="BULLISH",
            structure="CHoCH",
            structure_note="Change of Character detected.",
            resistance_range="$71,200 – $71,850",
            resistance_strength=78,
            support_range="$67,400 – $68,100",
            support_strength=86,
            risk_reward_ratio="1 : 3.42",
            risk_reward_probability=82,
            confidence=92,
            reasoning=(
                "BTC/USDT printed a clear Change of Character (CHoCH) after reclaiming the Fair Value Gap "
                "(FVG) above the 0.618 Fibonacci retracement. Price is holding above the 21 EMA with rising "
                "volume, favoring a continuation toward the upper supply zone while invalidation remains "
                "below the demand block."
            ),
            entry=_d("68400"),
            stop_loss=_d("67100"),
            take_profit=_d("69800"),
            overlays=overlays,
            is_saved=True,
        )
    )


async def main(email: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(User)
        if email:
            stmt = stmt.where(User.email == email.lower())
        users = list((await session.execute(stmt)).scalars().all())
        if not users:
            print("No users found.")
            return
        seeded = 0
        for user in users:
            before = await session.execute(
                select(AiAnalysis).where(
                    AiAnalysis.user_id == user.id,
                    AiAnalysis.symbol == "BTCUSDT",
                    AiAnalysis.is_saved.is_(True),
                )
            )
            if before.scalar_one_or_none():
                print(f"Skip {user.email}")
                continue
            await seed_for_user(session, user.id)
            seeded += 1
            print(f"Seeded AI analysis for {user.email}")
        await session.commit()
        print(f"Done. Seeded {seeded} user(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
