"""Seed paper trading desk sample data for users without an account.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_paper
  .venv\\Scripts\\python -m app.scripts.seed_paper --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.paper import (
    PaperAccount,
    PaperEquityPoint,
    PaperOrder,
    PaperPosition,
    PaperPositionEvent,
    PaperSentinelSuggestion,
)
from app.models.user import User


def _d(v: str | float | int) -> Decimal:
    return Decimal(str(v))


async def seed_for_user(session, user_id: UUID) -> None:
    existing = await session.execute(select(PaperAccount).where(PaperAccount.user_id == user_id))
    if existing.scalar_one_or_none() is not None:
        return

    now = datetime.now(timezone.utc)
    account = PaperAccount(
        user_id=user_id,
        cash=_d("1062500.00"),
        equity=_d("1248590.42"),
        starting_equity=_d("1200000.00"),
        win_rate_percent=_d("68.4"),
        total_pnl=_d("24310.15"),
        max_drawdown_percent=_d("2.15"),
        learning_mode="practice",
        fee_rate_bps=10,
    )
    session.add(account)
    await session.flush()

    positions = [
        {
            "symbol": "BTCUSDT",
            "side": "long",
            "size": "0.125",
            "entry": "64250",
            "current": "65890.4",
            "sl": "63100",
            "tp": "68500",
            "pnl": "2050.05",
            "health": "healthy",
            "lifecycle": "monitoring",
            "opened_delta": timedelta(hours=2),
            "notes": "Breakout continuation from demand zone.",
            "ai": "Continuation long after BOS. Holding while structure remains intact.",
            "future": "If price tags 66,200 with weak volume, consider partial TP.",
            "chart": "BTC 15m · Breakout continuation",
        },
        {
            "symbol": "ETHUSDT",
            "side": "short",
            "size": "2.4",
            "entry": "3480.2",
            "current": "3521.8",
            "sl": "3555",
            "tp": "3320",
            "pnl": "-99.84",
            "health": "watch",
            "lifecycle": "monitoring",
            "opened_delta": timedelta(hours=5),
            "notes": None,
            "ai": "Short under resistance; invalidation approaching.",
            "future": "Exam mode would score this as defensive management.",
            "chart": "ETH 1H · Resistance rejection",
        },
        {
            "symbol": "SOLUSDT",
            "side": "long",
            "size": "45",
            "entry": "148.2",
            "current": "152.6",
            "sl": "144.5",
            "tp": "162",
            "pnl": "198",
            "health": "near_tp",
            "lifecycle": "near_tp",
            "opened_delta": timedelta(minutes=45),
            "notes": None,
            "ai": "Momentum long approaching target.",
            "future": "Sentinel may recommend TP extension to 165.",
            "chart": "SOL 5m · Momentum run",
        },
    ]

    for i, p in enumerate(positions):
        size = _d(p["size"])
        base = p["symbol"].replace("USDT", "")
        pos = PaperPosition(
            account_id=account.id,
            symbol=p["symbol"],
            side=p["side"],
            size=size,
            size_label=f"{size} {base}",
            entry=_d(p["entry"]),
            current=_d(p["current"]),
            stop_loss=_d(p["sl"]),
            take_profit=_d(p["tp"]),
            unrealized_pnl=_d(p["pnl"]),
            realized_pnl=_d("0"),
            health=p["health"],
            lifecycle=p["lifecycle"],
            status="open",
            notes=p["notes"],
            ai_analysis=p["ai"],
            future_commentary=p["future"],
            chart_snapshot_label=p["chart"],
            risk_changes=[
                {"id": "r1", "label": "Initial risk", "value": "0.85%"},
                {"id": "r2", "label": "Current risk", "value": "0.42%"},
            ],
            trade_events=[
                {"id": "e1", "label": "Fill", "value": f"Opened {p['side']} {size} {base}"},
                {"id": "e2", "label": "SL set", "value": p["sl"]},
                {"id": "e3", "label": "TP set", "value": p["tp"]},
            ],
            execution_history=[
                {"id": "x1", "label": "open", "value": f"{p['side'].upper()} {size} @ {p['entry']}"},
            ],
            opened_at=now - p["opened_delta"],
        )
        session.add(pos)
        await session.flush()
        session.add(
            PaperPositionEvent(
                position_id=pos.id,
                time_label=(now - p["opened_delta"]).strftime("%H:%M"),
                title="Opened",
                detail=f"{p['side']} filled at {p['entry']}",
                sort_order=0,
            )
        )

    # Closed history
    for symbol, side, size, entry, exit_px, pnl, days in [
        ("BTCUSDT", "long", "0.08", "62800", "64120", "1056", 1),
        ("SOLUSDT", "short", "30", "156.4", "151.2", "156", 2),
    ]:
        base = symbol.replace("USDT", "")
        session.add(
            PaperPosition(
                account_id=account.id,
                symbol=symbol,
                side=side,
                size=_d(size),
                size_label=f"{size} {base}",
                entry=_d(entry),
                current=_d(exit_px),
                exit_price=_d(exit_px),
                stop_loss=None,
                take_profit=None,
                unrealized_pnl=_d("0"),
                realized_pnl=_d(pnl),
                health="healthy",
                lifecycle="closed",
                status="closed",
                ai_analysis="",
                future_commentary="",
                chart_snapshot_label="",
                risk_changes=[],
                trade_events=[],
                execution_history=[],
                opened_at=now - timedelta(days=days + 1),
                closed_at=now - timedelta(days=days),
            )
        )

    # Pending limits
    for symbol, side, size, limit_px, sl, tp, mins in [
        ("BTCUSDT", "long", "0.05", "63800", "62900", "67200", 12),
        ("ETHUSDT", "short", "1.2", "3560", "3610", "3400", 28),
    ]:
        base = symbol.replace("USDT", "")
        session.add(
            PaperOrder(
                account_id=account.id,
                symbol=symbol,
                side=side,
                order_type="limit",
                size=_d(size),
                size_label=f"{size} {base}",
                limit_price=_d(limit_px),
                stop_loss=_d(sl),
                take_profit=_d(tp),
                size_mode="fixed",
                status="pending",
                created_at=now - timedelta(minutes=mins),
            )
        )

    curves = {
        "1D": [("09:00", 1.21), ("11:00", 1.22), ("13:00", 1.225), ("15:00", 1.24), ("17:00", 1.248)],
        "1W": [
            ("Mon", 1.18),
            ("Tue", 1.2),
            ("Wed", 1.195),
            ("Thu", 1.22),
            ("Fri", 1.23),
            ("Sat", 1.242),
            ("Sun", 1.248),
        ],
        "1M": [("W1", 1.12), ("W2", 1.16), ("W3", 1.2), ("W4", 1.248)],
        "ALL": [
            ("Jan", 1.0),
            ("Mar", 1.08),
            ("May", 1.14),
            ("Jul", 1.18),
            ("Sep", 1.22),
            ("Nov", 1.248),
        ],
    }
    for range_key, pts in curves.items():
        for i, (label, value) in enumerate(pts):
            session.add(
                PaperEquityPoint(
                    account_id=account.id,
                    range_key=range_key,
                    label=label,
                    value=_d(value),
                    sort_order=i,
                )
            )

    session.add(
        PaperSentinelSuggestion(
            account_id=account.id,
            message=(
                "I've detected a high-probability reversal pattern on SOL/USDT. "
                "Recommend increasing Take Profit to 165.00 based on local volatility expansion."
            ),
            symbol="SOLUSDT",
            suggested_tp=_d("165"),
            is_active=True,
        )
    )


async def main(email: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(User)
        if email:
            stmt = stmt.where(User.email == email.lower())
        users = list((await session.execute(stmt)).scalars().all())
        if not users:
            print("No users found. Register first.")
            return
        seeded = 0
        for user in users:
            before = await session.execute(select(PaperAccount).where(PaperAccount.user_id == user.id))
            if before.scalar_one_or_none():
                print(f"Skip {user.email}")
                continue
            await seed_for_user(session, user.id)
            seeded += 1
            print(f"Seeded paper desk for {user.email}")
        await session.commit()
        print(f"Done. Seeded {seeded} user(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
