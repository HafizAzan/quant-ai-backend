"""Seed dashboard + portfolio read models for users without a portfolio.

Usage (from backend/):
  .venv\\Scripts\\python -m app.scripts.seed_portfolio
  .venv\\Scripts\\python -m app.scripts.seed_portfolio --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.portfolio import (
    ActivityEvent,
    AiAnalysisSummary,
    AiRecommendation,
    AllocationSlice,
    Holding,
    MonthlyReturn,
    OpenPosition,
    PerformancePoint,
    Portfolio,
    PortfolioHealthMetric,
    PortfolioTimelineEvent,
    TradingSignal,
    WatchlistItem,
)
from app.models.user import User

from datetime import datetime, timezone

DAY = 86400
BASE_DAY = int(datetime(2026, 7, 17, tzinfo=timezone.utc).timestamp())


def _d(value: str | float | int) -> Decimal:
    return Decimal(str(value))


def _day(offset: int) -> int:
    return BASE_DAY + offset * DAY


def _series(seed: list[float], scale: float = 1.0) -> list[tuple[int, Decimal]]:
    n = len(seed)
    return [(_day(i - n + 1), _d(v * scale)) for i, v in enumerate(seed)]


async def seed_for_user(session, user_id: UUID) -> None:
    existing = await session.execute(select(Portfolio).where(Portfolio.user_id == user_id))
    if existing.scalar_one_or_none() is not None:
        return

    portfolio = Portfolio(
        user_id=user_id,
        total_balance=_d("1248592.42"),
        unrealized_pnl=_d("142204.18"),
        realized_pnl_ytd=_d("84312.00"),
        equity=_d("1106388.24"),
        change_24h_percent=_d("2.4"),
        mtd_percent=_d("12.4"),
        daily_pnl=_d("14204"),
        weekly_pnl=_d("42912.18"),
        weekly_target_percent=_d("75"),
        ai_confidence_percent=_d("88"),
        ai_confidence_label="High Reliability",
        win_rate_percent=_d("68.4"),
        win_rate_period="Last 30 Days",
        win_streak="5 Trades",
        profit_factor=_d("2.41"),
        balance_spark=[48, 72, 28, 55, 42, 92, 52, 68],
        ai_score_overall=91,
        ai_score_risk="Low",
        ai_score_diversification="Excellent",
        ai_score_liquidity="Good",
        ai_score_volatility="Medium",
        ai_score_capital_allocation="Excellent",
        ai_score_recommendation=(
            "Reduce BTC allocation by 5% and increase stablecoin allocation to improve downside protection."
        ),
    )
    session.add(portfolio)
    await session.flush()

    holdings_data = [
        {
            "symbol": "TSLA",
            "name": "Tesla",
            "exchange": "NASDAQ",
            "quantity": "1240",
            "price": "178.22",
            "value": "220992.80",
            "pnl": "14240.50",
            "allocation": "17.7",
            "avg_entry": "166.74",
            "realized_pnl": "4200",
            "pinned": True,
            "overview": "Core equity long. Momentum intact above rising 50d.",
            "ai_analysis": "Strong relative strength vs QQQ. Concentration risk moderate.",
            "risk_assessment": "Beta elevated vs SPX. Keep size within equity band.",
            "suggested_actions": ["Trail stop under swing low", "Avoid adding above 5% weekly"],
            "trade_history": [
                {"id": "h1", "label": "Last buy", "value": "40 @ 171.20"},
                {"id": "h2", "label": "Realized YTD", "value": "+$4,200"},
            ],
        },
        {
            "symbol": "BTC",
            "name": "Bitcoin",
            "exchange": "BINANCE",
            "quantity": "2.8422",
            "price": "64812.21",
            "value": "184204.12",
            "pnl": "24102.11",
            "allocation": "14.8",
            "avg_entry": "56320",
            "realized_pnl": "18200",
            "overview": "Largest crypto allocation. High beta to risk-on.",
            "ai_analysis": "Overweight vs target. Correlation with SOL raises portfolio beta.",
            "risk_assessment": "Volatility Medium-High. Trim improves downside protection.",
            "suggested_actions": ["Reduce 5% into USDT", "Set alert at $62,500"],
            "trade_history": [
                {"id": "h1", "label": "Last buy", "value": "0.12 @ 63,400"},
                {"id": "h2", "label": "Realized YTD", "value": "+$18,200"},
            ],
        },
        {
            "symbol": "AAPL",
            "name": "Apple",
            "exchange": "NASDAQ",
            "quantity": "850",
            "price": "172.62",
            "value": "146727",
            "pnl": "-2110.45",
            "allocation": "11.8",
            "avg_entry": "175.1",
            "realized_pnl": "9100",
            "overview": "Defensive mega-cap. Currently underwater vs entry.",
            "ai_analysis": "Weak vs sector peers. Hold if thesis is quality compounder.",
            "risk_assessment": "Low idiosyncratic risk. Drag on short-term PnL.",
            "suggested_actions": ["Do not average down blindly", "Reassess at earnings"],
            "trade_history": [
                {"id": "h1", "label": "Last sell", "value": "50 @ 178.10"},
                {"id": "h2", "label": "Realized YTD", "value": "+$9,100"},
            ],
        },
        {
            "symbol": "NVDA",
            "name": "NVIDIA",
            "exchange": "NASDAQ",
            "quantity": "110",
            "price": "894.52",
            "value": "98397.20",
            "pnl": "42102.80",
            "allocation": "7.9",
            "avg_entry": "511.8",
            "realized_pnl": "22100",
            "pinned": True,
            "overview": "Strongest contributor YTD. Trend leader.",
            "ai_analysis": "Momentum exceptional. Protect gains with trailing logic.",
            "risk_assessment": "High single-name concentration. Cap adds.",
            "suggested_actions": ["Trail winner", "Partial take-profit on spike days"],
            "trade_history": [
                {"id": "h1", "label": "Last buy", "value": "10 @ 891.40"},
                {"id": "h2", "label": "Realized YTD", "value": "+$22,100"},
            ],
        },
    ]
    for i, h in enumerate(holdings_data):
        session.add(
            Holding(
                portfolio_id=portfolio.id,
                symbol=h["symbol"],
                name=h["name"],
                exchange=h["exchange"],
                quantity=_d(h["quantity"]),
                price=_d(h["price"]),
                value=_d(h["value"]),
                pnl=_d(h["pnl"]),
                allocation=_d(h["allocation"]),
                avg_entry=_d(h["avg_entry"]),
                realized_pnl=_d(h["realized_pnl"]),
                pinned=bool(h.get("pinned", False)),
                overview=h["overview"],
                ai_analysis=h["ai_analysis"],
                risk_assessment=h["risk_assessment"],
                suggested_actions=h["suggested_actions"],
                trade_history=h["trade_history"],
                sort_order=i,
            )
        )

    positions = [
        ("BTCUSDT", "Long", "10x", "0.45 BTC", "64120.00", "64850.20", "328.59", "1.14"),
        ("ETHUSDT", "Short", "5x", "2.10 ETH", "3480.00", "3421.40", "123.06", "1.68"),
        ("SOLUSDT", "Long", "8x", "45 SOL", "148.20", "152.80", "207.00", "3.10"),
        ("BNBUSDT", "Short", "3x", "8 BNB", "612.40", "618.90", "-52.00", "-1.06"),
    ]
    for i, (asset, side, lev, size, entry, mark, pnl, pnl_pct) in enumerate(positions):
        session.add(
            OpenPosition(
                user_id=user_id,
                asset=asset,
                side=side,
                leverage=lev,
                size=size,
                entry=_d(entry),
                mark=_d(mark),
                pnl=_d(pnl),
                pnl_percent=_d(pnl_pct),
                sort_order=i,
            )
        )

    equity_seed = [1.05, 1.06, 1.04, 1.08, 1.1, 1.09, 1.12, 1.15, 1.14, 1.18, 1.2, 1.19, 1.22, 1.24, 1.248]
    performance: dict[str, dict[str, list[tuple[int, Decimal]]]] = {
        "1D": {
            "equity": _series([1.22, 1.225, 1.23, 1.235, 1.24, 1.242, 1.248], 1_000_000),
            "unrealized": _series([120, 125, 128, 130, 135, 138, 142], 1000),
            "realized": _series([80, 81, 82, 82.5, 83, 83.5, 84.3], 1000),
            "balance": _series([1.22, 1.225, 1.23, 1.235, 1.24, 1.242, 1.248], 1_000_000),
            "benchmark": _series([1.2, 1.202, 1.205, 1.21, 1.212, 1.215, 1.218], 1_000_000),
        },
        "1W": {
            "equity": _series(equity_seed[-7:], 1_000_000),
            "unrealized": _series([110, 118, 125, 130, 135, 140, 142], 1000),
            "realized": _series([78, 79, 80, 81, 82, 83, 84.3], 1000),
            "balance": _series(equity_seed[-7:], 1_000_000),
            "benchmark": _series([1.1, 1.12, 1.13, 1.15, 1.16, 1.17, 1.18], 1_000_000),
        },
        "1M": {
            "equity": _series(equity_seed, 1_000_000),
            "unrealized": _series(
                [90, 95, 100, 110, 115, 120, 125, 128, 130, 132, 135, 138, 140, 141, 142], 1000
            ),
            "realized": _series([70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84.3], 1000),
            "balance": _series(equity_seed, 1_000_000),
            "benchmark": _series(
                [1.0, 1.02, 1.03, 1.05, 1.06, 1.07, 1.08, 1.1, 1.11, 1.12, 1.14, 1.15, 1.16, 1.17, 1.18],
                1_000_000,
            ),
        },
        "1Y": {
            "equity": _series(
                [0.9, 0.95, 0.98, 1.02, 1.05, 1.08, 1.1, 1.12, 1.15, 1.18, 1.2, 1.22, 1.24, 1.245, 1.248],
                1_000_000,
            ),
            "unrealized": _series([40, 50, 55, 60, 70, 80, 90, 100, 110, 120, 125, 130, 135, 140, 142], 1000),
            "realized": _series([20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 78, 82, 84.3], 1000),
            "balance": _series(
                [0.9, 0.95, 0.98, 1.02, 1.05, 1.08, 1.1, 1.12, 1.15, 1.18, 1.2, 1.22, 1.24, 1.245, 1.248],
                1_000_000,
            ),
            "benchmark": _series(
                [0.92, 0.94, 0.96, 0.99, 1.01, 1.03, 1.05, 1.07, 1.09, 1.11, 1.13, 1.15, 1.16, 1.17, 1.18],
                1_000_000,
            ),
        },
        "ALL": {
            "equity": _series(
                [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.18, 1.2, 1.22, 1.24, 1.248],
                1_000_000,
            ),
            "unrealized": _series([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 138, 142], 1000),
            "realized": _series([5, 10, 15, 20, 25, 30, 40, 45, 50, 55, 60, 70, 75, 80, 84.3], 1000),
            "balance": _series(
                [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.18, 1.2, 1.22, 1.24, 1.248],
                1_000_000,
            ),
            "benchmark": _series(
                [0.72, 0.76, 0.8, 0.84, 0.88, 0.92, 0.96, 1.0, 1.04, 1.08, 1.1, 1.12, 1.14, 1.16, 1.18],
                1_000_000,
            ),
        },
    }
    for range_key, series_map in performance.items():
        for series_kind, points in series_map.items():
            for t, value in points:
                session.add(
                    PerformancePoint(
                        user_id=user_id,
                        range_key=range_key,
                        series_kind=series_kind,
                        time=t,
                        value=value,
                    )
                )

    allocations = {
        "value": [
            ("equities", "Equities", "64.2", "#5b8def"),
            ("crypto", "Crypto", "22.8", "#22c55e"),
            ("cash", "Cash", "13.0", "#ec4899"),
        ],
        "risk": [
            ("high", "High Risk", "38", "#b91a24"),
            ("med", "Medium Risk", "41", "#eab308"),
            ("low", "Low Risk", "21", "#22c55e"),
        ],
        "sector": [
            ("tech", "Technology", "48", "#5b8def"),
            ("crypto", "Crypto", "23", "#22c55e"),
            ("cash", "Cash / Stables", "13", "#ec4899"),
            ("other", "Other", "16", "#8b8f9a"),
        ],
        "strategy": [
            ("trend", "Trend", "42", "#5b8def"),
            ("mean", "Mean Reversion", "28", "#22c55e"),
            ("ai", "AI Systematic", "18", "#adc6ff"),
            ("cash", "Cash Buffer", "12", "#ec4899"),
        ],
        "exchange": [
            ("binance", "Binance", "35", "#f0b90b"),
            ("nasdaq", "NASDAQ", "40", "#5b8def"),
            ("nyse", "NYSE", "12", "#22c55e"),
            ("cash", "Cash", "13", "#ec4899"),
        ],
    }
    for view, rows in allocations.items():
        for i, (key, label, pct, color) in enumerate(rows):
            session.add(
                AllocationSlice(
                    user_id=user_id,
                    view=view,
                    slice_key=key,
                    label=label,
                    percent=_d(pct),
                    color=color,
                    sort_order=i,
                )
            )

    monthly = [
        ("jan", "JAN", "4.2"),
        ("feb", "FEB", "1.8"),
        ("mar", "MAR", "-3.1"),
        ("apr", "APR", "6.4"),
        ("may", "MAY", "0.9"),
        ("jun", "JUN", "8.2"),
        ("jul", "JUL", None),
        ("aug", "AUG", "-0.4"),
        ("sep", "SEP", "2.8"),
        ("oct", "OCT", None),
        ("nov", "NOV", None),
        ("dec", "DEC", None),
    ]
    for i, (key, label, value) in enumerate(monthly):
        session.add(
            MonthlyReturn(
                user_id=user_id,
                period_key=key,
                label=label,
                value=None if value is None else _d(value),
                sort_order=i,
            )
        )

    health = [
        ("health", "Overall Health", "91/100", "success"),
        ("diversification", "Diversification", "Excellent", "success"),
        ("volatility", "Volatility", "Medium", "warning"),
        ("drawdown", "Max Drawdown", "-4.8%", "danger"),
        ("sharpe", "Sharpe Ratio", "1.84", "success"),
        ("sortino", "Sortino Ratio", "2.21", "success"),
        ("winrate", "Win Rate", "68.4%", "default"),
        ("exposure", "Risk Exposure", "1.8% daily", "warning"),
        ("expected", "Expected Monthly", "+3.2%", "success"),
        ("ai", "AI Confidence", "87%", "default"),
    ]
    for i, (key, label, value, tone) in enumerate(health):
        session.add(
            PortfolioHealthMetric(
                user_id=user_id,
                metric_key=key,
                label=label,
                value=value,
                tone=tone,
                sort_order=i,
            )
        )

    recommendations = [
        ("Reduce BTC exposure", "BTC is 14.8% of book — trim 5% into stables.", "warning"),
        ("Increase Cash", "Cash buffer at 13% — raise toward 18% ahead of CPI.", "info"),
        ("Diversify into ETH", "Crypto sleeve is BTC-heavy; ETH improves diversification.", "info"),
        ("Strong Momentum Detected", "NVDA trend intact — trail winners, do not chase size.", "success"),
        ("Rebalance Recommended", "Equities overweight vs target band by 4.2%.", "warning"),
    ]
    for i, (title, detail, severity) in enumerate(recommendations):
        session.add(
            AiRecommendation(
                user_id=user_id,
                title=title,
                detail=detail,
                severity=severity,
                sort_order=i,
            )
        )

    timeline = [
        ("Today 14:20", "ai_recommendation", "AI Recommendation", "Suggested BTC trim and stablecoin increase."),
        ("Yesterday", "buy", "Buy NVDA", "Added 10 shares @ $891.40"),
        ("3 days ago", "deposit", "Deposit", "+$25,000 USDT wired to portfolio."),
        ("Last week", "rebalance", "Rebalance", "Trimmed AAPL, rotated into cash buffer."),
        ("Last month", "milestone", "Portfolio Milestone", "Equity crossed $1.2M."),
    ]
    for i, (time_label, kind, title, detail) in enumerate(timeline):
        session.add(
            PortfolioTimelineEvent(
                user_id=user_id,
                time_label=time_label,
                kind=kind,
                title=title,
                detail=detail,
                sort_order=i,
            )
        )

    watchlist = [
        ("TSLA", "248.42", "2.14"),
        ("AAPL", "189.75", "-0.62"),
        ("EURUSD", "1.0842", "0"),
        ("NVDA", "875.30", "1.85"),
        ("GOLD", "2341.20", "-0.28"),
    ]
    for i, (symbol, price, change) in enumerate(watchlist):
        session.add(
            WatchlistItem(
                user_id=user_id,
                symbol=symbol,
                price=_d(price),
                change_percent=_d(change),
                sort_order=i,
            )
        )

    activity = [
        ("info", "AI Analysis Generated for BTC", "2 minutes ago"),
        ("success", "Buy order filled: 0.12 BTC", "8 minutes ago"),
        ("neutral", "Weekly performance report ready", "25 minutes ago"),
        ("success", "Strategy Momentum Bot activated", "1 hour ago"),
    ]
    for i, (etype, message, time_label) in enumerate(activity):
        session.add(
            ActivityEvent(
                user_id=user_id,
                event_type=etype,
                message=message,
                time_label=time_label,
                sort_order=i,
            )
        )

    signals = [
        ("BTC / USDT", "BUY", "64,201", "68,000", "Long"),
        ("ETH / USDT", "SELL", "3,421", "3,100", "Short"),
    ]
    for i, (pair, side, entry, target, position) in enumerate(signals):
        session.add(
            TradingSignal(
                user_id=user_id,
                pair=pair,
                side=side,
                entry=entry,
                target=target,
                position=position,
                sort_order=i,
                is_active=True,
            )
        )

    analyses = [
        ("BTC/USDT 4H", "BULLISH", "Strong bullish divergence on RSI accompanied by institutional buy...", 92),
        ("SPY 1D", "CORRECTION", "Macro liquidity draining from equity markets suggests short-term pullback...", 74),
        ("DXY 1H", "NEUTRAL", "Range-bound consolidation expected ahead of FOMC minutes. Volume...", 61),
    ]
    for i, (ticker, status, summary, confidence) in enumerate(analyses):
        session.add(
            AiAnalysisSummary(
                user_id=user_id,
                ticker=ticker,
                status=status,
                summary=summary,
                confidence=confidence,
                sort_order=i,
            )
        )


async def main(email: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(User)
        if email:
            stmt = stmt.where(User.email == email.lower())
        result = await session.execute(stmt)
        users = list(result.scalars().all())
        if not users:
            print("No users found. Register a user first, then re-run seed.")
            return

        seeded = 0
        for user in users:
            before = await session.execute(select(Portfolio).where(Portfolio.user_id == user.id))
            if before.scalar_one_or_none() is not None:
                print(f"Skip {user.email} (portfolio exists)")
                continue
            await seed_for_user(session, user.id)
            seeded += 1
            print(f"Seeded portfolio for {user.email}")

        await session.commit()
        print(f"Done. Seeded {seeded} user(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None, help="Seed only this user email")
    args = parser.parse_args()
    asyncio.run(main(args.email))
