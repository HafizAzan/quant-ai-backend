"""Seed strategies + canvases + sample backtests.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_strategies
  .venv\\Scripts\\python -m app.scripts.seed_strategies --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.strategy import BacktestRun, Strategy, StrategyEdge, StrategyNode
from app.models.user import User


def _d(v: str | float | int) -> Decimal:
    return Decimal(str(v))


def _label(dt: datetime) -> str:
    return dt.strftime("%b %d, %Y")


async def seed_for_user(session, user_id: UUID) -> None:
    existing = await session.execute(select(Strategy).where(Strategy.user_id == user_id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    now = datetime.now(timezone.utc)

    seeds = [
        {
            "name": "Momentum Alpha V4",
            "symbol": "BTC/USDT",
            "timeframe": "5m",
            "status": "active",
            "win_rate": "68.4",
            "profit_factor": "2.14",
            "drawdown": "12.5",
            "backtest_age": timedelta(days=2),
            "description": "Momentum continuation strategy that sells into overbought RSI while price holds above the 200 EMA structure.",
            "markets": ["BTC/USDT", "ETH/USDT"],
            "timeframes": ["5m", "15m"],
            "version": "v4.2.1",
            "created_age": timedelta(days=120),
            "ai_confidence": 84,
            "estimated_risk": "medium",
            "estimated_monthly_return": "+6.2%",
            "strategy_type": "Momentum",
            "tags": ["crypto", "intraday", "rsi"],
            "nodes": [
                {
                    "node_key": "trigger",
                    "category": "trigger",
                    "type_id": "market_open",
                    "title": "TRIGGER: MARKET OPEN",
                    "description": "Asset: BTC/USDT",
                    "validation": "valid",
                    "ports": [{"id": "out", "side": "out"}],
                },
                {
                    "node_key": "condition",
                    "category": "condition",
                    "type_id": "condition_group",
                    "title": "CONDITION GROUP (AND)",
                    "lines": ["IF RSI (14) > 70", "AND EMA (200) is Below Price"],
                    "validation": "valid",
                    "ports": [
                        {"id": "in", "side": "in"},
                        {"id": "out-true", "side": "out", "label": "true"},
                        {"id": "out-false", "side": "out", "label": "false"},
                    ],
                },
                {
                    "node_key": "sell",
                    "category": "action",
                    "type_id": "action_sell",
                    "title": "ACTION: SELL",
                    "description": "Execute market sell order for 15% of portfolio.",
                    "validation": "valid",
                    "ports": [{"id": "in", "side": "in"}],
                },
                {
                    "node_key": "wait",
                    "category": "action",
                    "type_id": "action_wait",
                    "title": "ACTION: WAIT",
                    "description": "Re-evaluate in next candle (5m).",
                    "validation": "idle",
                    "ports": [{"id": "in", "side": "in"}],
                },
            ],
            "edges": [
                {"edge_key": "e1", "source_key": "trigger", "target_key": "condition", "source_port": "out", "target_port": "in"},
                {
                    "edge_key": "e2",
                    "source_key": "condition",
                    "target_key": "sell",
                    "source_port": "out-true",
                    "target_port": "in",
                    "label": "true",
                },
                {
                    "edge_key": "e3",
                    "source_key": "condition",
                    "target_key": "wait",
                    "source_port": "out-false",
                    "target_port": "in",
                    "label": "false",
                },
            ],
            "backtest": {
                "win_rate": "68.4",
                "profit_factor": "2.14",
                "drawdown": "12.5",
                "sharpe": "1.42",
                "trades": 186,
                "monthly_return": "+6.2%",
            },
        },
        {
            "name": "Mean Reversion Pro",
            "symbol": "ETH/USDT",
            "timeframe": "1h",
            "status": "paused",
            "win_rate": "54.2",
            "profit_factor": "1.45",
            "drawdown": "8.1",
            "backtest_age": timedelta(days=6),
            "description": "Mean-reversion entries near lower Bollinger bands with RSI confirmation and tight risk controls.",
            "markets": ["ETH/USDT"],
            "timeframes": ["1h", "4h"],
            "version": "v2.0.0",
            "created_age": timedelta(days=200),
            "ai_confidence": 71,
            "estimated_risk": "low",
            "estimated_monthly_return": "+3.1%",
            "strategy_type": "Mean Reversion",
            "tags": ["eth", "swing"],
            "nodes": [
                {
                    "node_key": "trigger",
                    "category": "trigger",
                    "type_id": "market_open",
                    "title": "TRIGGER: CANDLE CLOSE",
                    "description": "Asset: ETH/USDT",
                    "validation": "valid",
                    "ports": [{"id": "out", "side": "out"}],
                },
                {
                    "node_key": "condition",
                    "category": "condition",
                    "type_id": "condition_group",
                    "title": "CONDITION GROUP (AND)",
                    "lines": ["IF RSI (14) < 30", "AND Price near lower Bollinger"],
                    "validation": "warning",
                    "ports": [
                        {"id": "in", "side": "in"},
                        {"id": "out-true", "side": "out", "label": "true"},
                        {"id": "out-false", "side": "out", "label": "false"},
                    ],
                },
                {
                    "node_key": "buy",
                    "category": "action",
                    "type_id": "action_buy",
                    "title": "ACTION: BUY",
                    "description": "Enter long with 10% portfolio risk.",
                    "validation": "valid",
                    "ports": [{"id": "in", "side": "in"}],
                },
                {
                    "node_key": "wait",
                    "category": "action",
                    "type_id": "action_wait",
                    "title": "ACTION: WAIT",
                    "description": "Skip until RSI recovers above 35.",
                    "validation": "idle",
                    "ports": [{"id": "in", "side": "in"}],
                },
            ],
            "edges": [
                {"edge_key": "e1", "source_key": "trigger", "target_key": "condition"},
                {"edge_key": "e2", "source_key": "condition", "target_key": "buy", "label": "true"},
                {"edge_key": "e3", "source_key": "condition", "target_key": "wait", "label": "false"},
            ],
            "backtest": {
                "win_rate": "54.2",
                "profit_factor": "1.45",
                "drawdown": "8.1",
                "sharpe": "0.98",
                "trades": 112,
                "monthly_return": "+3.1%",
            },
        },
        {
            "name": "Volatility Breakout",
            "symbol": "SOL/USDT",
            "timeframe": "15m",
            "status": "active",
            "win_rate": "72.1",
            "profit_factor": "3.02",
            "drawdown": "18.4",
            "backtest_age": timedelta(days=4),
            "description": "ATR expansion breakout with volume confirmation and trailing stop management.",
            "markets": ["SOL/USDT", "BTC/USDT"],
            "timeframes": ["15m", "1h"],
            "version": "v1.8.0",
            "created_age": timedelta(days=90),
            "ai_confidence": 79,
            "estimated_risk": "high",
            "estimated_monthly_return": "+9.4%",
            "strategy_type": "Breakout",
            "tags": ["sol", "volatility"],
            "nodes": [
                {
                    "node_key": "trigger",
                    "category": "trigger",
                    "type_id": "market_open",
                    "title": "TRIGGER: RANGE BREAK",
                    "description": "Asset: SOL/USDT",
                    "validation": "valid",
                    "ports": [{"id": "out", "side": "out"}],
                },
                {
                    "node_key": "condition",
                    "category": "condition",
                    "type_id": "condition_group",
                    "title": "CONDITION GROUP (AND)",
                    "lines": ["IF ATR (14) expanding", "AND Volume > 1.5x average"],
                    "validation": "valid",
                    "ports": [
                        {"id": "in", "side": "in"},
                        {"id": "out-true", "side": "out", "label": "true"},
                        {"id": "out-false", "side": "out", "label": "false"},
                    ],
                },
                {
                    "node_key": "sell",
                    "category": "action",
                    "type_id": "action_buy",
                    "title": "ACTION: LONG",
                    "description": "Breakout entry with trailing stop at 1.5 ATR.",
                    "validation": "valid",
                    "ports": [{"id": "in", "side": "in"}],
                },
                {
                    "node_key": "wait",
                    "category": "action",
                    "type_id": "action_wait",
                    "title": "ACTION: WAIT",
                    "description": "No breakout confirmation — hold cash.",
                    "validation": "idle",
                    "ports": [{"id": "in", "side": "in"}],
                },
            ],
            "edges": [
                {"edge_key": "e1", "source_key": "trigger", "target_key": "condition"},
                {"edge_key": "e2", "source_key": "condition", "target_key": "sell", "label": "true"},
                {"edge_key": "e3", "source_key": "condition", "target_key": "wait", "label": "false"},
            ],
            "backtest": {
                "win_rate": "72.1",
                "profit_factor": "3.02",
                "drawdown": "18.4",
                "sharpe": "1.88",
                "trades": 94,
                "monthly_return": "+9.4%",
            },
        },
    ]

    for s in seeds:
        sid = uuid4()
        created = now - s["created_age"]
        backtested = now - s["backtest_age"]
        session.add(
            Strategy(
                id=sid,
                user_id=user_id,
                name=s["name"],
                symbol=s["symbol"],
                timeframe=s["timeframe"],
                status=s["status"],
                description=s["description"],
                markets=s["markets"],
                timeframes=s["timeframes"],
                version=s["version"],
                ai_confidence=s["ai_confidence"],
                estimated_risk=s["estimated_risk"],
                estimated_monthly_return=s["estimated_monthly_return"],
                win_rate=_d(s["win_rate"]),
                profit_factor=_d(s["profit_factor"]),
                drawdown=_d(s["drawdown"]),
                max_drawdown=_d(s["drawdown"]),
                exchange="Binance",
                strategy_type=s["strategy_type"],
                tags=s["tags"],
                author="QuantAI Lab",
                last_backtest_at=backtested,
                last_backtest_label=_label(backtested),
                created_at=created,
                updated_at=backtested,
            )
        )
        for i, n in enumerate(s["nodes"]):
            session.add(
                StrategyNode(
                    id=uuid4(),
                    strategy_id=sid,
                    node_key=n["node_key"],
                    category=n["category"],
                    type_id=n["type_id"],
                    title=n["title"],
                    description=n.get("description"),
                    lines=n.get("lines"),
                    collapsed=False,
                    validation=n.get("validation", "idle"),
                    config=n.get("config"),
                    ports=n.get("ports"),
                    sort_order=i,
                )
            )
        for e in s["edges"]:
            session.add(
                StrategyEdge(
                    id=uuid4(),
                    strategy_id=sid,
                    edge_key=e["edge_key"],
                    source_key=e["source_key"],
                    target_key=e["target_key"],
                    source_port=e.get("source_port"),
                    target_port=e.get("target_port"),
                    label=e.get("label"),
                    highlighted=False,
                    errored=False,
                )
            )
        b = s["backtest"]
        metrics = {
            "win_rate": float(b["win_rate"]),
            "profit_factor": float(b["profit_factor"]),
            "drawdown": float(b["drawdown"]),
            "sharpe": float(b["sharpe"]),
            "trades": b["trades"],
            "monthly_return": b["monthly_return"],
        }
        session.add(
            BacktestRun(
                id=uuid4(),
                strategy_id=sid,
                user_id=user_id,
                status="completed",
                symbol=s["symbol"],
                timeframe=s["timeframe"],
                range_label="90d",
                win_rate=_d(b["win_rate"]),
                profit_factor=_d(b["profit_factor"]),
                drawdown=_d(b["drawdown"]),
                sharpe=_d(b["sharpe"]),
                trades=b["trades"],
                monthly_return=b["monthly_return"],
                metrics=metrics,
                started_at=backtested,
                finished_at=backtested,
                created_at=backtested,
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
            before = await session.execute(select(Strategy).where(Strategy.user_id == user.id).limit(1))
            if before.scalar_one_or_none():
                print(f"Skip {user.email}")
                continue
            await seed_for_user(session, user.id)
            seeded += 1
            print(f"Seeded strategies for {user.email}")
        await session.commit()
        print(f"Done. Seeded {seeded} user(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
