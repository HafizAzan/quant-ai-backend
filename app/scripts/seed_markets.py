"""Seed markets assets + sample candles + snapshot.

Usage (from backend/):
  .venv\\Scripts\\python -m app.scripts.seed_markets
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.market import Asset, Candle, MarketSnapshot

SEED_ASSETS: list[dict] = [
    {
        "symbol": "BTC",
        "trading_pair": "BTCUSDT",
        "name": "Bitcoin",
        "rank": 1,
        "price": "64820.40",
        "change_24h": "2.45",
        "volume_24h": "28400000000",
        "market_cap": "1270000000000",
        "ai_signal": "Strong Buy",
        "color": "#F7931A",
        "is_high_volume": True,
        "is_crypto_ai": True,
    },
    {
        "symbol": "ETH",
        "trading_pair": "ETHUSDT",
        "name": "Ethereum",
        "rank": 2,
        "price": "3421.18",
        "change_24h": "-1.12",
        "volume_24h": "14200000000",
        "market_cap": "411500000000",
        "ai_signal": "Neutral",
        "color": "#627EEA",
        "is_high_volume": True,
        "is_crypto_ai": True,
    },
    {
        "symbol": "SOL",
        "trading_pair": "SOLUSDT",
        "name": "Solana",
        "rank": 3,
        "price": "152.80",
        "change_24h": "4.87",
        "volume_24h": "3800000000",
        "market_cap": "71200000000",
        "ai_signal": "Buy",
        "color": "#14F195",
        "is_high_volume": True,
        "is_crypto_ai": True,
    },
    {
        "symbol": "BNB",
        "trading_pair": "BNBUSDT",
        "name": "BNB",
        "rank": 4,
        "price": "612.40",
        "change_24h": "0.64",
        "volume_24h": "1900000000",
        "market_cap": "89400000000",
        "ai_signal": "Buy",
        "color": "#F3BA2F",
        "is_high_volume": True,
    },
    {
        "symbol": "XRP",
        "trading_pair": "XRPUSDT",
        "name": "XRP",
        "rank": 5,
        "price": "0.6241",
        "change_24h": "-2.31",
        "volume_24h": "2100000000",
        "market_cap": "35800000000",
        "ai_signal": "Sell",
        "color": "#23292F",
        "is_high_volume": True,
    },
    {
        "symbol": "ADA",
        "trading_pair": "ADAUSDT",
        "name": "Cardano",
        "rank": 6,
        "price": "0.4820",
        "change_24h": "1.08",
        "volume_24h": "640000000",
        "market_cap": "17100000000",
        "ai_signal": "Neutral",
        "color": "#0033AD",
        "is_new_listing": False,
        "is_crypto_ai": True,
    },
]

# From frontend ai-analysis-data chartCandles (1h)
BTC_1H_CANDLES: list[tuple[int, float, float, float, float, float]] = [
    (1719705600, 67240, 67480, 67110, 67390, 812),
    (1719709200, 67390, 67620, 67280, 67550, 940),
    (1719712800, 67550, 67710, 67340, 67420, 705),
    (1719716400, 67420, 67580, 67180, 67260, 990),
    (1719720000, 67260, 67490, 67140, 67410, 860),
    (1719723600, 67410, 67880, 67370, 67790, 1120),
    (1719727200, 67790, 68120, 67680, 68040, 1280),
    (1719730800, 68040, 68210, 67820, 67910, 970),
    (1719734400, 67910, 68100, 67640, 67720, 1040),
    (1719738000, 67720, 68050, 67610, 67980, 1180),
    (1719741600, 67980, 68440, 67920, 68360, 1410),
    (1719745200, 68360, 68720, 68280, 68610, 1520),
    (1719748800, 68610, 68840, 68350, 68480, 1090),
    (1719752400, 68480, 68690, 68120, 68240, 1210),
    (1719756000, 68240, 68580, 68100, 68490, 1330),
    (1719759600, 68490, 68910, 68420, 68780, 1600),
    (1719763200, 68780, 69020, 68560, 68640, 1140),
    (1719766800, 68640, 68940, 68480, 68820, 1260),
    (1719770400, 68820, 69280, 68740, 69150, 1710),
    (1719774000, 69150, 69420, 68910, 69040, 1480),
    (1719777600, 69040, 69380, 68860, 69270, 1550),
    (1719781200, 69270, 69640, 69120, 69510, 1680),
    (1719784800, 69510, 69780, 69240, 69380, 1390),
    (1719788400, 69380, 69610, 68280, 68432.12, 2140),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Asset).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Markets already seeded — skipping.")
            return

        assets_by_pair: dict[str, Asset] = {}
        for item in SEED_ASSETS:
            asset = Asset(
                symbol=item["symbol"],
                trading_pair=item["trading_pair"],
                name=item["name"],
                category="crypto",
                rank=item["rank"],
                price=Decimal(item["price"]),
                change_24h=Decimal(item["change_24h"]),
                volume_24h=Decimal(item["volume_24h"]),
                market_cap=Decimal(item["market_cap"]),
                ai_signal=item["ai_signal"],
                color=item["color"],
                is_high_volume=bool(item.get("is_high_volume", False)),
                is_new_listing=bool(item.get("is_new_listing", False)),
                is_crypto_ai=bool(item.get("is_crypto_ai", False)),
                is_active=True,
            )
            session.add(asset)
            assets_by_pair[asset.trading_pair] = asset

        await session.flush()

        btc = assets_by_pair["BTCUSDT"]
        for open_time, o, h, l, c, v in BTC_1H_CANDLES:
            session.add(
                Candle(
                    asset_id=btc.id,
                    trading_pair="BTCUSDT",
                    timeframe="1h",
                    open_time=open_time,
                    open=Decimal(str(o)),
                    high=Decimal(str(h)),
                    low=Decimal(str(l)),
                    close=Decimal(str(c)),
                    volume=Decimal(str(v)),
                )
            )

        # Simple synthetic 1h candles for ETH/SOL from last BTC shape scaled
        for pair, base in (("ETHUSDT", 3400.0), ("SOLUSDT", 150.0)):
            asset = assets_by_pair[pair]
            for open_time, o, h, l, c, v in BTC_1H_CANDLES:
                scale = base / 68000.0
                session.add(
                    Candle(
                        asset_id=asset.id,
                        trading_pair=pair,
                        timeframe="1h",
                        open_time=open_time,
                        open=Decimal(str(round(o * scale, 4))),
                        high=Decimal(str(round(h * scale, 4))),
                        low=Decimal(str(round(l * scale, 4))),
                        close=Decimal(str(round(c * scale, 4))),
                        volume=Decimal(str(v)),
                    )
                )

        session.add(
            MarketSnapshot(
                fear_greed_score=74,
                fear_greed_zone="Greed",
                fear_greed_description="Retail sentiment elevated. Institutional volume +12% vs weekly avg.",
                btc_dominance=Decimal("54.10"),
                alts_dominance=Decimal("32.40"),
                stables_dominance=Decimal("13.50"),
                ai_pick_symbol="SOL",
                ai_pick_confidence=Decimal("94.20"),
            )
        )

        await session.commit()
        print(f"Seeded {len(SEED_ASSETS)} assets + candles + market snapshot.")


if __name__ == "__main__":
    asyncio.run(seed())
