"""Seed alerts desk sample data.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_alerts
  .venv\\Scripts\\python -m app.scripts.seed_alerts --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.alert import (
    Alert,
    AlertCondition,
    AlertTimelineEvent,
    AlertTrigger,
    AlertWatchItem,
    NotificationChannel,
)
from app.models.user import User
from app.services.alert_service import DEFAULT_CHANNELS


def _d(v: str | float | int) -> Decimal:
    return Decimal(str(v))


async def seed_for_user(session, user_id: UUID) -> None:
    existing = await session.execute(select(Alert).where(Alert.user_id == user_id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    now = datetime.now(timezone.utc)

    # channels
    ch = await session.execute(select(NotificationChannel).where(NotificationChannel.user_id == user_id).limit(1))
    if ch.scalar_one_or_none() is None:
        for kind, label, status, rate, latency in DEFAULT_CHANNELS:
            session.add(
                NotificationChannel(
                    user_id=user_id,
                    kind=kind,
                    label=label,
                    status=status,
                    success_rate=rate,
                    latency=latency,
                    last_delivery_at=now - timedelta(minutes=12) if status == "connected" else None,
                    config={},
                )
            )

    seeds = [
        {
            "symbol": "BTCUSDT",
            "title": "Price Crossing Above $65,000",
            "category": "price",
            "priority": "high",
            "frequency": "recurring",
            "channels": ["push", "telegram", "webhook"],
            "operator": "above",
            "target": "65000",
            "entry": "65000",
            "enabled": True,
            "age": timedelta(days=2),
            "last": timedelta(minutes=12),
            "explanation": {
                "whyTriggered": "Spot price printed above the $65,000 threshold with rising volume.",
                "marketStructure": "Bullish continuation after higher-low reclaim.",
                "supportingIndicators": ["Volume spike", "VWAP reclaim", "Funding neutral"],
                "confidence": 86,
                "suggestedAction": "Open AI Analysis and evaluate long continuation vs resistance.",
                "riskLevel": "Medium",
                "probability": "72% continuation within 4h",
                "relatedAssets": ["ETH/USDT", "SOL/USDT"],
            },
            "timeline": [
                ("created", "2d ago", "Alert created from Markets"),
                ("triggered", "12m ago", "Price crossed $65,000"),
                ("acknowledged", "10m ago", "Delivered to Telegram + Webhook"),
            ],
        },
        {
            "symbol": "ETHUSDT",
            "title": "RSI (14) Overbought > 70",
            "category": "technical",
            "priority": "medium",
            "frequency": "recurring",
            "channels": ["push", "discord"],
            "operator": "above",
            "target": "3500",
            "entry": None,
            "enabled": True,
            "age": timedelta(days=5),
            "last": timedelta(hours=1),
            "explanation": {
                "whyTriggered": "RSI(14) crossed above 70 on the 1h timeframe.",
                "marketStructure": "Extended move into supply; watch for CHoCH.",
                "supportingIndicators": ["RSI 72.4", "ATR elevated", "OI rising"],
                "confidence": 74,
                "suggestedAction": "Ask AI for mean-reversion vs trend-continuation bias.",
                "riskLevel": "Medium-High",
                "probability": "58% pullback within session",
                "relatedAssets": ["BTC/USDT"],
            },
            "timeline": [
                ("created", "5d ago", "Technical rule saved"),
                ("triggered", "1h ago", "RSI > 70"),
            ],
        },
        {
            "symbol": "SOLUSDT",
            "title": "High-probability demand reclaim setup",
            "category": "ai_signal",
            "priority": "critical",
            "frequency": "one_time",
            "channels": ["telegram", "webhook", "push"],
            "operator": "above",
            "target": "148.2",
            "entry": "148.2",
            "sl": "145.5",
            "tp": "155",
            "enabled": True,
            "age": timedelta(hours=6),
            "last": timedelta(hours=6),
            "explanation": {
                "whyTriggered": "AI detected liquidity sweep into demand with bullish BOS confirmation.",
                "marketStructure": "Bullish BOS on 15m after sweep of equal lows.",
                "supportingIndicators": ["BOS", "Demand zone", "Volume imbalance"],
                "confidence": 87,
                "suggestedAction": "Open chart, paper trade first, then size live if structure holds.",
                "riskLevel": "Controlled",
                "probability": "87% setup quality",
                "relatedAssets": ["BTC/USDT"],
            },
            "timeline": [
                ("created", "6h ago", "AI agent generated alert"),
                ("triggered", "6h ago", "Setup confirmed"),
                ("executed", "5h ago", "User opened AI Analysis"),
            ],
        },
        {
            "symbol": "BTCUSDT",
            "title": "Break of Structure on 15m",
            "category": "bos",
            "priority": "high",
            "frequency": "recurring",
            "channels": ["webhook"],
            "operator": "above",
            "target": "66000",
            "entry": None,
            "enabled": False,
            "age": timedelta(days=1),
            "last": None,
            "explanation": {
                "whyTriggered": "Reserved for next BOS confirmation above prior swing high.",
                "marketStructure": "Currently ranging under resistance.",
                "supportingIndicators": ["Swing map", "Session VWAP"],
                "confidence": 80,
                "suggestedAction": "Keep muted until London open volatility rises.",
                "riskLevel": "Low while disabled",
                "probability": "Pending trigger",
                "relatedAssets": ["ETH/USDT"],
            },
            "timeline": [("created", "1d ago", "Structure alert armed")],
        },
    ]

    for s in seeds:
        alert = Alert(
            user_id=user_id,
            symbol=s["symbol"],
            title=s["title"],
            category=s["category"],
            priority=s["priority"],
            frequency=s["frequency"],
            channels=s["channels"],
            enabled=s["enabled"],
            status="active",
            entry=_d(s["entry"]) if s.get("entry") else None,
            stop_loss=_d(s["sl"]) if s.get("sl") else None,
            take_profit=_d(s["tp"]) if s.get("tp") else None,
            explanation=s["explanation"],
            last_triggered_at=(now - s["last"]) if s.get("last") else None,
            trigger_count_24h=1 if s.get("last") else 0,
            created_at=now - s["age"],
        )
        session.add(alert)
        await session.flush()
        session.add(
            AlertCondition(
                alert_id=alert.id,
                condition_type="price" if s["category"] == "price" else s["category"],
                operator=s["operator"],
                target_value=_d(s["target"]),
                logic="and",
                sort_order=0,
            )
        )
        for i, (kind, time_label, detail) in enumerate(s["timeline"]):
            session.add(
                AlertTimelineEvent(
                    alert_id=alert.id,
                    kind=kind,
                    time_label=time_label,
                    detail=detail,
                    sort_order=i,
                )
            )
        if s.get("last"):
            session.add(
                AlertTrigger(
                    alert_id=alert.id,
                    user_id=user_id,
                    symbol=s["symbol"],
                    badge="TRIGGERED" if s["category"] == "price" else "AI SIGNAL",
                    badge_tone="warning" if s["category"] == "price" else "accent",
                    detail=s["title"],
                    mark_price=_d(s["target"]),
                    delivered=True,
                    created_at=now - s["last"],
                )
            )

    watch = [
        ("BTC", "High Probability Setup", 87, "success"),
        ("ETH", "Waiting for BOS", None, "accent"),
        ("SOL", "Near Demand Zone", None, "success"),
        ("XAUUSD", "Liquidity Sweep Detected", None, "warning"),
        ("NASDAQ", "High News Risk", None, "danger"),
        ("DXY", "Trend Reversal Possible", None, "warning"),
    ]
    for i, (symbol, status, confidence, tone) in enumerate(watch):
        session.add(
            AlertWatchItem(
                user_id=user_id,
                symbol=symbol,
                status=status,
                confidence=confidence,
                tone=tone,
                sort_order=i,
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
            before = await session.execute(select(Alert).where(Alert.user_id == user.id).limit(1))
            if before.scalar_one_or_none():
                print(f"Skip {user.email}")
                continue
            await seed_for_user(session, user.id)
            seeded += 1
            print(f"Seeded alerts for {user.email}")
        await session.commit()
        print(f"Done. Seeded {seeded} user(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
