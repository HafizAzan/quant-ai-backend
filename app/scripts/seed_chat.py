"""Seed AI chat threads + sample messages.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_chat
  .venv\\Scripts\\python -m app.scripts.seed_chat --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.chat import ChatMessage, ChatThread
from app.models.user import User
from app.services.command_resolver import resolve_platform_command, to_execution_result


async def seed_for_user(session, user_id: UUID) -> None:
    existing = await session.execute(select(ChatThread).where(ChatThread.user_id == user_id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    now = datetime.now(timezone.utc)

    threads = [
        {
            "title": "BTC Trend Analysis Q4",
            "preview": "Analyzing bullish divergence on the 4H timeframe...",
            "symbol": "BTC/USDT",
            "bias": "bullish",
            "confidence": 82,
            "age": timedelta(hours=2),
            "tokens": 1482,
            "messages": [
                {
                    "role": "user",
                    "content": "Analyze the top 3 performing assets in the tech sector over the last 24 hours.",
                    "offset": timedelta(minutes=30),
                },
                {
                    "role": "assistant",
                    "content": None,
                    "offset": timedelta(minutes=29),
                    "sections": [
                        {
                            "id": "exec",
                            "title": "Executive Summary",
                            "default_open": True,
                            "blocks": [
                                {
                                    "type": "text",
                                    "text": "Tech-correlated crypto assets are outperforming on the 24h window, led by SOL with strong NFT and institutional flow.",
                                }
                            ],
                        },
                        {
                            "id": "performers",
                            "title": "Top Performers",
                            "default_open": True,
                            "blocks": [
                                {
                                    "type": "table",
                                    "columns": [
                                        {"key": "asset", "header": "Asset"},
                                        {"key": "performance", "header": "Performance"},
                                        {"key": "spxCorr", "header": "SPX Corr"},
                                    ],
                                    "trend_key": "performanceValue",
                                    "rows": [
                                        {
                                            "asset": "SOL/USD",
                                            "performance": "+12.4%",
                                            "performanceValue": 12.4,
                                            "spxCorr": "0.42",
                                        },
                                        {
                                            "asset": "LINK/USD",
                                            "performance": "+8.7%",
                                            "performanceValue": 8.7,
                                            "spxCorr": "0.58",
                                        },
                                        {
                                            "asset": "BTC/USD",
                                            "performance": "+5.2%",
                                            "performanceValue": 5.2,
                                            "spxCorr": "0.71",
                                        },
                                    ],
                                },
                                {
                                    "type": "callout",
                                    "tone": "info",
                                    "text": "SOL is currently leading the sector due to high NFT volume and institutional inflows.",
                                },
                            ],
                        },
                        {
                            "id": "confidence",
                            "title": "Confidence",
                            "default_open": False,
                            "blocks": [
                                {
                                    "type": "text",
                                    "text": "Signal confidence: 78% — based on volume confirmation and cross-exchange flow consistency.",
                                }
                            ],
                        },
                    ],
                },
                {
                    "role": "user",
                    "content": "What does this chart pattern suggest for BTC?",
                    "image_label": "BTC 4H wedge pattern",
                    "offset": timedelta(minutes=20),
                },
                {
                    "role": "assistant",
                    "content": None,
                    "offset": timedelta(minutes=19),
                    "sections": [
                        {
                            "id": "exec-2",
                            "title": "Executive Summary",
                            "default_open": True,
                            "blocks": [
                                {
                                    "type": "text",
                                    "text": "BTC is forming a classic ascending wedge near resistance with tapering volume — a setup that often precedes a liquidity sweep.",
                                }
                            ],
                        },
                        {
                            "id": "structure",
                            "title": "Market Structure",
                            "default_open": True,
                            "blocks": [
                                {
                                    "type": "list",
                                    "items": [
                                        "Higher lows intact on the 4H",
                                        "Resistance compression into the wedge apex",
                                        "Volume declining into the pattern",
                                    ],
                                },
                                {
                                    "type": "callout",
                                    "tone": "warning",
                                    "text": "Avoid chasing breakouts before a confirmed close beyond the wedge boundary.",
                                },
                            ],
                        },
                        {
                            "id": "setup",
                            "title": "Trade Setup",
                            "default_open": True,
                            "blocks": [
                                {
                                    "type": "text",
                                    "text": "Bias long only after reclaim of the apex with volume. Invalidation sits below the demand zone under the rising trendline.",
                                },
                                {
                                    "type": "code",
                                    "language": "setup",
                                    "code": "Entry: reclaim of wedge apex\nSL: below demand zone\nTP1: prior swing high\nTP2: measured move of wedge height",
                                },
                            ],
                        },
                    ],
                },
                {
                    "role": "user",
                    "content": "Show my Portfolio",
                    "offset": timedelta(minutes=5),
                },
                {
                    "role": "assistant",
                    "content": "Understood — treating this as a platform command. I can open Portfolio and surface positions, PnL, and exposure from there.",
                    "offset": timedelta(minutes=4),
                    "command_raw": "Show my Portfolio",
                },
            ],
        },
        {
            "title": "ETH Whale Activity",
            "preview": "Large inflow detected across major exchanges...",
            "symbol": "ETH/USDT",
            "bias": "bullish",
            "confidence": 74,
            "age": timedelta(days=1),
            "tokens": 920,
            "messages": [
                {
                    "role": "user",
                    "content": "Summarize ETH whale activity today",
                    "offset": timedelta(hours=1),
                },
                {
                    "role": "assistant",
                    "content": "Large ETH inflows detected across major exchanges with rising spot bid liquidity.",
                    "offset": timedelta(minutes=55),
                    "blocks": [
                        {
                            "type": "callout",
                            "tone": "success",
                            "text": "Net exchange inflow elevated vs 7d average — bias cautiously bullish.",
                        }
                    ],
                },
            ],
        },
        {
            "title": "S&P 500 Correlation",
            "preview": "Cross-asset analysis vs crypto beta...",
            "symbol": "SPX",
            "bias": "neutral",
            "confidence": 61,
            "age": timedelta(days=3),
            "tokens": 640,
            "messages": [
                {
                    "role": "user",
                    "content": "How correlated is BTC with SPX this week?",
                    "offset": timedelta(hours=2),
                },
                {
                    "role": "assistant",
                    "content": "BTC-SPX rolling 30d correlation sits near 0.71 — risk-on beta remains elevated.",
                    "offset": timedelta(hours=1, minutes=55),
                },
            ],
        },
    ]

    for t in threads:
        thread_id = uuid4()
        created = now - t["age"]
        session.add(
            ChatThread(
                id=thread_id,
                user_id=user_id,
                title=t["title"],
                preview=t["preview"],
                symbol=t["symbol"],
                bias=t["bias"],
                confidence=t["confidence"],
                engine="GPT-4o-Market-Enhanced",
                tokens_used=t["tokens"],
                tokens_limit=32000,
                created_at=created,
                updated_at=created,
            )
        )
        for m in t["messages"]:
            command_result = None
            if m.get("command_raw"):
                intent = resolve_platform_command(m["command_raw"])
                if intent:
                    command_result = to_execution_result(intent)
            session.add(
                ChatMessage(
                    id=uuid4(),
                    thread_id=thread_id,
                    role=m["role"],
                    content=m.get("content"),
                    image_label=m.get("image_label"),
                    sections=m.get("sections"),
                    blocks=m.get("blocks"),
                    command_result=command_result,
                    stream_status="complete",
                    created_at=created + m["offset"],
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
            before = await session.execute(select(ChatThread).where(ChatThread.user_id == user.id).limit(1))
            if before.scalar_one_or_none():
                print(f"Skip {user.email}")
                continue
            await seed_for_user(session, user.id)
            seeded += 1
            print(f"Seeded chat for {user.email}")
        await session.commit()
        print(f"Done. Seeded {seeded} user(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
