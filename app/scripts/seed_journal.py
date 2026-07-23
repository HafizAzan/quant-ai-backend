"""Seed journal desk sample data.

Usage:
  .venv\\Scripts\\python -m app.scripts.seed_journal
  .venv\\Scripts\\python -m app.scripts.seed_journal --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.journal import JournalCoachItem, JournalEntry, JournalProfile, JournalTimelineEvent
from app.models.user import User


def _d(v: str | float | int) -> Decimal:
    return Decimal(str(v))


def _ts(base: datetime, offset_hours: float) -> int:
    return int((base + timedelta(hours=offset_hours)).timestamp())


def _build_candles(start_ts: int, count: int, seed: float, drift: float) -> list[dict]:
    candles: list[dict] = []
    price = seed
    for i in range(count):
        open_ = price
        move = math.sin(i / 2) * drift + (drift * 0.4 if i % 3 == 0 else -drift * 0.2)
        close = open_ + move
        high = max(open_, close) + drift * 0.35
        low = min(open_, close) - drift * 0.35
        candles.append(
            {
                "time": start_ts + i * 900,
                "open": round(open_, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
            }
        )
        price = close
    return candles


async def seed_for_user(session, user_id: UUID) -> None:
    existing = await session.execute(select(JournalEntry).where(JournalEntry.user_id == user_id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    now = datetime.now(timezone.utc)
    # Keep relative chart times near "today" so 30d filter includes them
    day_a = now - timedelta(days=1)
    day_b = now - timedelta(days=2)

    profile = JournalProfile(
        id=uuid4(),
        user_id=user_id,
        level="Intermediate Trader",
        overall_score=84,
        discipline=91,
        psychology=73,
        risk_management=88,
        execution=81,
        biggest_weakness="Exiting winning trades too early.",
        current_mission="Hold profitable trades until predefined Take Profit unless market structure changes.",
        estimated_improvement="+12% Win Rate if completed.",
        analytics={
            "win_rate": "64.5%",
            "profit_factor": "2.84",
            "avg_win": "$842.00",
            "avg_loss": "-$291.50",
            "avg_rr": "1:2.1",
            "avg_holding": "2h 14m",
            "max_drawdown": "-3.8%",
            "expectancy": "$214.20",
            "best_day": "Tuesday",
            "worst_day": "Friday open",
            "most_traded": "BTC/USDT",
            "best_timeframe": "15m",
            "best_strategy": "Scalping",
        },
        patterns=[
            {"id": "best-hours", "label": "Best Trading Hours", "value": "13:00–16:00 UTC", "tone": "success"},
            {"id": "worst-hours", "label": "Worst Trading Hours", "value": "07:00–09:00 UTC", "tone": "danger"},
            {"id": "best-asset", "label": "Best Asset", "value": "BTC/USDT", "tone": "success"},
            {"id": "worst-asset", "label": "Worst Asset", "value": "ETH/USDT", "tone": "danger"},
            {"id": "best-strat", "label": "Most Profitable Strategy", "value": "Scalping", "tone": "success"},
            {"id": "mistake", "label": "Most Common Mistake", "value": "Early Exit", "tone": "warning"},
            {"id": "psych", "label": "Psychology Pattern", "value": "Impatience on winners", "tone": "warning"},
            {"id": "streak", "label": "Winning Streak", "value": "4 trades", "tone": "success"},
        ],
        allocation=[
            {"id": "btc", "label": "BTC", "percent": 60},
            {"id": "eth", "label": "ETH", "percent": 25},
            {"id": "sol", "label": "SOL", "percent": 15},
        ],
        monthly_progress=[
            {"id": "consistency", "label": "Consistency", "value": "82%", "tone": "success"},
            {"id": "discipline", "label": "Discipline", "value": "91%", "tone": "success"},
            {"id": "risk", "label": "Risk Score", "value": "88%", "tone": "success"},
            {"id": "psych", "label": "Psychology", "value": "73%", "tone": "warning"},
            {"id": "execution", "label": "Execution", "value": "81%", "tone": "default"},
            {"id": "strategy", "label": "Strategy Improvement", "value": "+6%", "tone": "success"},
            {"id": "learning", "label": "AI Learning Progress", "value": "64%", "tone": "default"},
            {"id": "growth", "label": "Portfolio Growth", "value": "+8.2%", "tone": "success"},
        ],
        daily_pnl=[
            {"time": _ts(now, -24 * 6), "value": 120},
            {"time": _ts(now, -24 * 5), "value": -80},
            {"time": _ts(now, -24 * 4), "value": 240},
            {"time": _ts(now, -24 * 3), "value": 90},
            {"time": _ts(now, -24 * 2), "value": -40},
            {"time": _ts(now, -24), "value": 310},
            {"time": _ts(now, 0), "value": 180},
        ],
        strategy_insight={
            "title": "AI Strategy Insight",
            "body": "ETH shorts during 07:00–09:00 UTC underperform. Shift ETH activity to London–NY overlap or skip.",
            "action_label": "Apply Filter Analysis",
        },
    )
    session.add(profile)

    coach_items = [
        ("Review today's trades", "2 wins, 1 loss. Early exits remain the primary edge leak.", "Open review"),
        ("Explain repeated mistakes", "Early exit appears in 67% of winning trades this week.", "See pattern"),
        ("Weekly improvement plan", "Mission: hold to TP. Target +12% win-rate lift.", "Start mission"),
    ]
    for i, (title, detail, action) in enumerate(coach_items):
        session.add(
            JournalCoachItem(
                id=uuid4(),
                user_id=user_id,
                title=title,
                detail=detail,
                action_label=action,
                sort_order=i,
            )
        )

    btc_start = _ts(day_a, -6)
    eth_start = _ts(day_a, -10)
    sol_start = _ts(day_b, -4)

    entries = [
        {
            "traded_at": day_a.replace(hour=14, minute=22, second=0, microsecond=0),
            "date_group": day_a.strftime("%B %d, %Y").upper(),
            "symbol": "BTC/USDT",
            "side": "long",
            "strategy_tag": "SCALPING",
            "emotion_tag": "Focused",
            "timeframe": "15m",
            "market_condition": "Trending",
            "outcome": "win",
            "pnl": "1240.50",
            "roi": "2.4",
            "risk_reward": "1:2.8",
            "duration": "1h 42m",
            "exited_at": "14:22",
            "entry_price": "64250",
            "exit_price": "65890",
            "stop_loss": "63800",
            "take_profit": "66100",
            "notes": "Felt calm. Stuck to plan after BOS confirmation.",
            "psychology_notes": "No urge to move SL. Slight impatience near TP.",
            "ai_summary": "Strong execution. Entry after liquidity sweep and BOS. Slight early exit vs full TP — patience score capped.",
            "score": {
                "overall": 88,
                "entry_quality": 92,
                "exit_quality": 74,
                "risk_management": 90,
                "psychology": 78,
                "execution": 91,
                "patience": 68,
                "rule_compliance": 94,
                "grade": "A",
            },
            "mistakes": ["early_exit"],
            "improvement": {
                "went_well": ["Waited for BOS", "Risk sized to 0.5%", "SL below structure"],
                "went_wrong": ["Took profit before planned TP"],
                "should_improve": ["Let winners run to structure TP"],
                "alternative_entry": "Limit at demand mid after sweep",
                "alternative_exit": "Scale 50% at 65,600, trail remainder",
                "better_stop_loss": "63,720 (true swing low)",
                "better_take_profit": "66,100 as planned",
                "professional_tips": ["Partial at +1.5R reduces FOMO to exit early"],
                "next_focus": "Hold to predefined TP unless CHoCH against you",
            },
            "candles": _build_candles(btc_start, 28, 64200, 80),
            "entry_time": _ts(day_a, -4),
            "exit_time": _ts(day_a, -2.3),
            "timeline": [
                ("market_analysis", "12:30", "Market Analysis", "Bullish structure on 15m"),
                ("signal", "12:38", "Signal Generated", "AI BOS + demand reclaim"),
                ("opened", "12:40", "Trade Opened", "Long @ 64,250"),
                ("managed", "13:20", "Position Managed", "Held through minor pullback"),
                ("final_exit", "14:22", "Final Exit", "Closed @ 65,890"),
                ("ai_review", "14:25", "AI Review Completed", "Score 88 · Grade A"),
            ],
        },
        {
            "traded_at": day_a.replace(hour=11, minute=10, second=0, microsecond=0),
            "date_group": day_a.strftime("%B %d, %Y").upper(),
            "symbol": "ETH/USDT",
            "side": "short",
            "strategy_tag": "BREAKOUT",
            "emotion_tag": "Anxious",
            "timeframe": "1h",
            "market_condition": "Volatile",
            "outcome": "loss",
            "pnl": "-312.40",
            "roi": "-1.1",
            "risk_reward": "1:1.6",
            "duration": "3h 05m",
            "exited_at": "11:10",
            "entry_price": "3520",
            "exit_price": "3558",
            "stop_loss": "3560",
            "take_profit": "3420",
            "notes": "Entered after missing first impulse. Felt rushed.",
            "psychology_notes": "FOMO after seeing BTC run. Wanted “action”.",
            "ai_summary": "FOMO short against higher-timeframe support. Size slightly elevated. Classic late entry mistake.",
            "score": {
                "overall": 42,
                "entry_quality": 35,
                "exit_quality": 55,
                "risk_management": 48,
                "psychology": 28,
                "execution": 50,
                "patience": 30,
                "rule_compliance": 40,
                "grade": "D",
            },
            "mistakes": ["fomo_entry", "late_entry", "emotional_trading"],
            "improvement": {
                "went_well": ["Honored stop loss"],
                "went_wrong": ["Chased after move", "Ignored HTF support"],
                "should_improve": ["Wait for reclaim failure confirmation"],
                "alternative_entry": "Short only after failed reclaim of 3,540",
                "alternative_exit": "Cut earlier at -0.5R when thesis broke",
                "better_stop_loss": "3,555 tight invalidation",
                "better_take_profit": "3,420 only if structure confirms",
                "professional_tips": ["No trade after missing the move — journal FOMO trigger"],
                "next_focus": "Zero FOMO entries for 5 sessions",
            },
            "candles": _build_candles(eth_start, 24, 3480, 12),
            "entry_time": _ts(day_a, -8),
            "exit_time": _ts(day_a, -5),
            "timeline": [
                ("market_analysis", "07:50", "Market Analysis", "Saw BTC strength, forced ETH short"),
                ("opened", "08:05", "Trade Opened", "Short @ 3,520"),
                ("final_exit", "11:10", "Final Exit", "Stopped @ 3,558"),
                ("ai_review", "11:12", "AI Review Completed", "Score 42 · Grade D"),
            ],
        },
        {
            "traded_at": day_b.replace(hour=18, minute=40, second=0, microsecond=0),
            "date_group": day_b.strftime("%B %d, %Y").upper(),
            "symbol": "SOL/USDT",
            "side": "long",
            "strategy_tag": "SWING",
            "emotion_tag": "Patient",
            "timeframe": "1h",
            "market_condition": "Range -> Break",
            "outcome": "win",
            "pnl": "486.20",
            "roi": "3.1",
            "risk_reward": "1:2.2",
            "duration": "6h 18m",
            "exited_at": "18:40",
            "entry_price": "148.2",
            "exit_price": "152.9",
            "stop_loss": "145.8",
            "take_profit": "154.0",
            "notes": "Good wait for break and retest.",
            "psychology_notes": "Calm. Followed checklist.",
            "ai_summary": "Textbook break-retest long. Exit slightly early again — pattern matches biggest weakness.",
            "score": {
                "overall": 86,
                "entry_quality": 94,
                "exit_quality": 72,
                "risk_management": 89,
                "psychology": 88,
                "execution": 90,
                "patience": 70,
                "rule_compliance": 92,
                "grade": "A",
            },
            "mistakes": ["early_exit"],
            "improvement": {
                "went_well": ["Retest entry", "Clear invalidation", "Sized correctly"],
                "went_wrong": ["Closed before TP"],
                "should_improve": ["Use staged exits"],
                "alternative_entry": None,
                "alternative_exit": "40% at 152, trail rest to 154",
                "better_stop_loss": None,
                "better_take_profit": None,
                "professional_tips": ["Mission: hold to TP unless CHoCH"],
                "next_focus": "Execute staged TP plan",
            },
            "candles": _build_candles(sol_start, 20, 148, 1.2),
            "entry_time": _ts(day_b, -6),
            "exit_time": _ts(day_b, 0),
            "timeline": [
                ("signal", "12:10", "Signal Generated", "Break + retest"),
                ("opened", "12:22", "Trade Opened", "Long @ 148.20"),
                ("partial_exit", "16:00", "Partial Exit", "Scaled 30%"),
                ("final_exit", "18:40", "Final Exit", "Closed remainder"),
                ("ai_review", "18:45", "AI Review Completed", "Score 86 · Grade A"),
            ],
        },
    ]

    for s in entries:
        entry_id = uuid4()
        session.add(
            JournalEntry(
                id=entry_id,
                user_id=user_id,
                symbol=s["symbol"],
                side=s["side"],
                strategy_tag=s["strategy_tag"],
                emotion_tag=s["emotion_tag"],
                timeframe=s["timeframe"],
                market_condition=s["market_condition"],
                outcome=s["outcome"],
                pnl=_d(s["pnl"]),
                roi_percent=_d(s["roi"]),
                risk_reward=s["risk_reward"],
                duration=s["duration"],
                exited_at_label=s["exited_at"],
                entry_price=_d(s["entry_price"]),
                exit_price=_d(s["exit_price"]),
                stop_loss=_d(s["stop_loss"]),
                take_profit=_d(s["take_profit"]),
                notes=s["notes"],
                psychology_notes=s["psychology_notes"],
                ai_summary=s["ai_summary"],
                score=s["score"],
                mistakes=s["mistakes"],
                improvement=s["improvement"],
                candles=s["candles"],
                entry_time=s["entry_time"],
                exit_time=s["exit_time"],
                traded_at=s["traded_at"],
                date_group=s["date_group"],
            )
        )
        for i, (kind, time_label, title, detail) in enumerate(s["timeline"]):
            session.add(
                JournalTimelineEvent(
                    id=uuid4(),
                    entry_id=entry_id,
                    kind=kind,
                    time_label=time_label,
                    title=title,
                    detail=detail,
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
            before = await session.execute(select(JournalEntry).where(JournalEntry.user_id == user.id).limit(1))
            if before.scalar_one_or_none():
                print(f"Skip {user.email}")
                continue
            await seed_for_user(session, user.id)
            seeded += 1
            print(f"Seeded journal for {user.email}")
        await session.commit()
        print(f"Done. Seeded {seeded} user(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.email))
