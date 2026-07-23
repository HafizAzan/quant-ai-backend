"""Seed live trading desk sample data.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_live
  .venv\\Scripts\\python -m app.scripts.seed_live --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.live import (
    LiveAccount,
    LiveActivityEvent,
    LiveBalance,
    LiveGuardianAlert,
    LiveOrder,
    LivePosition,
)
from app.models.user import User
from app.services.live_service import DEFAULT_EXPOSURE, DEFAULT_MONITOR, DEFAULT_RISK, DEFAULT_STATUS


def _d(v: str | float | int) -> Decimal:
    return Decimal(str(v))


async def seed_for_user(session, user_id: UUID) -> None:
    existing = await session.execute(select(LiveAccount).where(LiveAccount.user_id == user_id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    account_id = uuid4()
    session.add(
        LiveAccount(
            id=account_id,
            user_id=user_id,
            exchange="Binance",
            api_active=True,
            auto_trading=False,
            trading_locked=False,
            risk_only_mode=False,
            default_leverage=10,
            margin_type="cross",
            total_unrealized_pnl=_d("1245.20"),
            risk_controls=dict(DEFAULT_RISK),
            portfolio_exposure=dict(DEFAULT_EXPOSURE),
            system_status=list(DEFAULT_STATUS),
            market_monitor=list(DEFAULT_MONITOR),
        )
    )

    for i, (asset, amount, ch) in enumerate(
        [("USDT", "84,250.40", "2.4"), ("BTC", "1.2840", "1.2"), ("ETH", "12.450", "-0.8")]
    ):
        session.add(
            LiveBalance(
                id=uuid4(),
                account_id=account_id,
                asset=asset,
                amount=amount,
                change_24h=_d(ch),
                sort_order=i,
            )
        )

    positions = [
        {
            "symbol": "BTCUSDT",
            "side": "long",
            "size": "0.50",
            "entry": "64200",
            "mark": "65890.4",
            "leverage": 10,
            "pnl": "845.20",
            "health": "healthy",
            "sl": "63100",
            "tp": "68500",
            "detail": {
                "timeline": [
                    {"id": "t1", "time": "12:04", "title": "Opened", "detail": "Market long 0.50 BTC @ 64,200"},
                    {"id": "t2", "time": "13:20", "title": "Monitoring", "detail": "Structure intact above demand"},
                    {"id": "t3", "time": "14:10", "title": "AI note", "detail": "Trail SL suggested to 64,800"},
                ],
                "ai_analysis": "Continuation long after BOS. Risk is within guardian limits.",
                "entry_reason": "Break of structure + reclaim of session VWAP.",
                "current_risk": "0.62% account · 1.4R open",
                "stop_loss_history": [
                    {"id": "s1", "label": "Initial", "value": "63,100"},
                    {"id": "s2", "label": "Current", "value": "63,100"},
                ],
                "take_profit_history": [
                    {"id": "p1", "label": "Initial", "value": "68,500"},
                    {"id": "p2", "label": "Current", "value": "68,500"},
                ],
                "ai_suggestions": ["Move SL to breakeven at +1R", "Scale 25% at 66,200"],
                "trade_events": [
                    {"id": "e1", "label": "Fill", "value": "BUY 0.50 @ 64,200"},
                    {"id": "e2", "label": "Fees", "value": "$12.84"},
                ],
                "market_snapshot": "BTC 15m · Bullish structure · Funding neutral",
            },
        },
        {
            "symbol": "ETHUSDT",
            "side": "short",
            "size": "4.20",
            "entry": "3480",
            "mark": "3521.8",
            "leverage": 8,
            "pnl": "-175.56",
            "health": "monitoring",
            "sl": "3560",
            "tp": "3320",
            "detail": {
                "timeline": [
                    {"id": "t1", "time": "10:12", "title": "Opened", "detail": "Short 4.20 ETH @ 3,480"},
                    {"id": "t2", "time": "14:12", "title": "Risk alert", "detail": "Approaching drawdown limit"},
                ],
                "ai_analysis": "Short thesis weakening. Reduce or tighten risk.",
                "entry_reason": "Rejection at resistance with declining OI.",
                "current_risk": "1.1% account · -0.4R",
                "stop_loss_history": [{"id": "s1", "label": "Current", "value": "3,560"}],
                "take_profit_history": [{"id": "p1", "label": "Current", "value": "3,320"}],
                "ai_suggestions": ["Cut 30% size", "Move SL to 3,540"],
                "trade_events": [{"id": "e1", "label": "Fill", "value": "SELL 4.20 @ 3,480"}],
                "market_snapshot": "ETH 1H · Resistance test · Vol elevated",
            },
        },
        {
            "symbol": "SOLUSDT",
            "side": "long",
            "size": "120",
            "entry": "148.2",
            "mark": "152.6",
            "leverage": 5,
            "pnl": "528",
            "health": "near_tp",
            "sl": "144",
            "tp": "155",
            "detail": {
                "timeline": [
                    {"id": "t1", "time": "13:40", "title": "Opened", "detail": "Long 120 SOL @ 148.20"},
                    {"id": "t2", "time": "14:18", "title": "Near TP", "detail": "AI recommends partial take profit"},
                ],
                "ai_analysis": "Momentum long near target. Protect gains.",
                "entry_reason": "Bullish divergence + volume expansion.",
                "current_risk": "0.25% account · +1.9R",
                "stop_loss_history": [{"id": "s1", "label": "Current", "value": "144.00"}],
                "take_profit_history": [{"id": "p1", "label": "Current", "value": "155.00"}],
                "ai_suggestions": ["Take 40% profit", "Trail remainder"],
                "trade_events": [{"id": "e1", "label": "Fill", "value": "BUY 120 @ 148.20"}],
                "market_snapshot": "SOL 5m · Momentum · Near TP",
            },
        },
        {
            "symbol": "LINKUSDT",
            "side": "long",
            "size": "200",
            "entry": "14.9",
            "mark": "14.62",
            "leverage": 7,
            "pnl": "-56",
            "health": "near_sl",
            "sl": "14.55",
            "tp": "16.2",
            "detail": {
                "timeline": [
                    {"id": "t1", "time": "13:55", "title": "Opened", "detail": "Long 200 LINK @ 14.90"},
                    {"id": "t2", "time": "14:20", "title": "Near SL", "detail": "Price within stop noise band"},
                ],
                "ai_analysis": "Weak hold. Decide cut vs reclaim.",
                "entry_reason": "Mean reversion into demand.",
                "current_risk": "0.9% account · -0.6R",
                "stop_loss_history": [{"id": "s1", "label": "Current", "value": "14.55"}],
                "take_profit_history": [{"id": "p1", "label": "Current", "value": "16.20"}],
                "ai_suggestions": ["Exit if 14.55 prints", "Do not average down"],
                "trade_events": [{"id": "e1", "label": "Fill", "value": "BUY 200 @ 14.90"}],
                "market_snapshot": "LINK 15m · Weak · Near SL",
            },
        },
    ]

    for p in positions:
        session.add(
            LivePosition(
                id=uuid4(),
                account_id=account_id,
                symbol=p["symbol"],
                side=p["side"],
                size=_d(p["size"]),
                size_label=p["size"],
                entry=_d(p["entry"]),
                mark=_d(p["mark"]),
                leverage=p["leverage"],
                margin_type="cross",
                unrealized_pnl=_d(p["pnl"]),
                health=p["health"],
                stop_loss=_d(p["sl"]),
                take_profit=_d(p["tp"]),
                status="open",
                detail=p["detail"],
            )
        )

    orders = [
        ("BTCUSDT", "long", "limit", "Limit Buy", "63800", "0.15", "0"),
        ("ETHUSDT", "short", "stop", "Stop Loss", "3560", "4.20", "0"),
        ("DOTUSDT", "long", "limit", "Limit Buy", "7.42", "500", "12"),
    ]
    for symbol, side, otype, label, price, amount, filled in orders:
        session.add(
            LiveOrder(
                id=uuid4(),
                account_id=account_id,
                symbol=symbol,
                side=side,
                order_type=otype,
                type_label=label,
                price=_d(price),
                amount=_d(amount),
                amount_label=amount,
                filled_percent=_d(filled),
                leverage=10,
                margin_type="cross",
                status="open",
            )
        )

    activities = [
        ("14:22:08", "Order Filled", "Bought 0.05 BTC @ 65,890.40", "order_filled", "success"),
        (
            "14:18:41",
            "AI Recommendation",
            "Bullish divergence detected on SOL 15m — consider partial TP.",
            "ai_recommendation",
            "info",
        ),
        (
            "14:12:03",
            "Risk Alert",
            "Position 'ETH Short' approaching 1% drawdown limit.",
            "risk_alert",
            "warning",
        ),
        ("14:05:17", "Exchange Status", "Exchange connection synchronized with Binance.", "exchange_status", "info"),
        ("13:58:22", "Order Placed", "Limit Buy DOTUSDT placed successfully.", "system", "success"),
        ("13:44:09", "Trailing Stop Updated", "SOL long trail moved to 149.80", "trailing_stop", "info"),
    ]
    now = datetime.now(timezone.utc)
    for ts, title, detail, category, severity in activities:
        session.add(
            LiveActivityEvent(
                id=uuid4(),
                account_id=account_id,
                timestamp_label=ts,
                title=title,
                detail=detail,
                category=category,
                severity=severity,
                created_at=now,
            )
        )

    guardians = [
        (
            "Correlated exposure",
            "BTC + SOL longs increase directional beta. Consider reducing size.",
            "warning",
            "Reduce SOL",
        ),
        ("ETH short pressure", "Price approaching stop. Suggest move SL or cut 30%.", "warning", "Adjust SL"),
        ("Volatility elevated", "1h ATR above 7d average — lower leverage recommended.", "info", "Lower lev"),
    ]
    for i, (title, detail, severity, action) in enumerate(guardians):
        session.add(
            LiveGuardianAlert(
                id=uuid4(),
                account_id=account_id,
                title=title,
                detail=detail,
                severity=severity,
                action_label=action,
                sort_order=i,
                active=True,
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
            before = await session.execute(select(LiveAccount).where(LiveAccount.user_id == user.id).limit(1))
            if before.scalar_one_or_none():
                print(f"Skip {user.email}")
                continue
            await seed_for_user(session, user.id)
            seeded += 1
            print(f"Seeded live trading for {user.email}")
        await session.commit()
        print(f"Done. Seeded {seeded} user(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
