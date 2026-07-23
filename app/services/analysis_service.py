from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AiAnalysis
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import (
    AlertDraftOut,
    AnalysisListItemOut,
    AnalysisListOut,
    AnalysisOut,
    AiSignalPanelOut,
    GenerateAnalysisRequest,
    SupplyDemandOut,
    TradeMetricsOut,
    WorkspaceMetaOut,
    WorkspaceOut,
)

ALLOWED_TIMEFRAMES = {"1m", "5m", "15m", "1h", "4h", "1d", "1w"}

SYMBOLS = [
    {"value": "BTCUSDT", "label": "BTC / USDT"},
    {"value": "ETHUSDT", "label": "ETH / USDT"},
    {"value": "SOLUSDT", "label": "SOL / USDT"},
]

TIMEFRAMES = [
    {"id": "1m", "label": "1m"},
    {"id": "5m", "label": "5m"},
    {"id": "15m", "label": "15m"},
    {"id": "1h", "label": "1h"},
    {"id": "4h", "label": "4h"},
    {"id": "1d", "label": "1d"},
    {"id": "1w", "label": "1w"},
]

LAYOUTS = [
    {"value": "single", "label": "Single"},
    {"value": "split", "label": "Split"},
    {"value": "multi", "label": "Multi"},
]

FALLBACK_PRICES = {
    "BTCUSDT": Decimal("68432.12"),
    "ETHUSDT": Decimal("3421.18"),
    "SOLUSDT": Decimal("152.80"),
}


def _q(value: Decimal, places: str = "0.01") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace("/", "").replace("-", "").replace(" ", "")


def _pair_label(symbol: str) -> str:
    s = _normalize_symbol(symbol)
    if s.endswith("USDT") and len(s) > 4:
        return f"{s[:-4]} / USDT"
    return s


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def _build_overlays(
    *,
    close: Decimal,
    entry: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    resistance: Decimal,
    support: Decimal,
    supply_from: Decimal,
    supply_to: Decimal,
    demand_from: Decimal,
    demand_to: Decimal,
    marker_time: int | None,
) -> dict:
    overlays = {
        "priceLines": [
            {
                "id": "resistance",
                "kind": "resistance",
                "price": float(resistance),
                "title": "RESISTANCE",
                "color": "#b91a24",
            },
            {
                "id": "support",
                "kind": "support",
                "price": float(support),
                "title": "SUPPORT",
                "color": "#22c55e",
            },
            {
                "id": "tp1",
                "kind": "take_profit",
                "price": float(take_profit),
                "title": "TP1",
                "color": "#5b8def",
            },
            {
                "id": "entry",
                "kind": "entry",
                "price": float(entry),
                "title": "ENTRY",
                "color": "#5b8def",
            },
            {
                "id": "sl",
                "kind": "stop_loss",
                "price": float(stop_loss),
                "title": "SL",
                "color": "#b91a24",
            },
        ],
        "zones": [
            {
                "id": "supply-1",
                "kind": "supply",
                "from": float(supply_from),
                "to": float(supply_to),
                "label": "Supply",
                "color": "#b91a24",
            },
            {
                "id": "demand-1",
                "kind": "demand",
                "from": float(demand_from),
                "to": float(demand_to),
                "label": "Demand",
                "color": "#22c55e",
            },
        ],
        "markers": [],
        "annotations": [],
    }
    if marker_time:
        overlays["markers"].append(
            {
                "id": "choch-1",
                "time": marker_time,
                "position": "belowBar",
                "shape": "arrowUp",
                "color": "#adc6ff",
                "text": "CHoCH",
            }
        )
    # keep close available for consumers
    overlays["_close"] = float(close)
    return overlays


class AnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AnalysisRepository(session)

    async def _resolve_quote(self, symbol: str, timeframe: str, lookback: int) -> dict:
        asset = await self.repo.get_asset(symbol)
        candles = await self.repo.list_candles(symbol, timeframe, lookback)

        if candles:
            first = candles[0]
            last = candles[-1]
            high = max(c.high for c in candles)
            low = min(c.low for c in candles)
            open_price = first.open
            close_price = last.close
            change = Decimal("0")
            if open_price > 0:
                change = _q(((close_price - open_price) / open_price) * 100, "0.01")
            vol = sum((c.volume or Decimal(0)) for c in candles)
            return {
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "change_percent": change,
                "volume_label": f"{float(vol):,.0f}",
                "candles": candles,
                "change_24h": asset.change_24h if asset else change,
            }

        close = asset.price if asset else FALLBACK_PRICES.get(symbol, Decimal("100"))
        change = asset.change_24h if asset else Decimal("0")
        return {
            "open": _q(close * Decimal("0.992")),
            "high": _q(close * Decimal("1.01")),
            "low": _q(close * Decimal("0.988")),
            "close": close,
            "change_percent": change,
            "volume_label": "n/a",
            "candles": [],
            "change_24h": change,
        }

    def _synthesize(self, symbol: str, quote: dict) -> dict:
        close: Decimal = quote["close"]
        high: Decimal = quote["high"]
        low: Decimal = quote["low"]
        change: Decimal = quote["change_percent"]

        bullish = change >= 0
        entry = _q(close * Decimal("0.9995"), "0.00000001")
        if bullish:
            stop_loss = _q(close * Decimal("0.981"), "0.00000001")
            take_profit = _q(close * Decimal("1.02"), "0.00000001")
            trend = "BULLISH"
            structure = "CHoCH"
            structure_note = "Change of Character detected."
            confidence = 82
            probability = 82
        else:
            stop_loss = _q(close * Decimal("1.019"), "0.00000001")
            take_profit = _q(close * Decimal("0.98"), "0.00000001")
            trend = "BEARISH"
            structure = "BOS"
            structure_note = "Break of structure favoring sellers."
            confidence = 74
            probability = 71

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr = _q(reward / risk, "0.01") if risk > 0 else Decimal("0")

        resistance = _q(max(high, close) * Decimal("1.03"))
        support = _q(min(low, close) * Decimal("0.993"))
        supply_from = _q(resistance * Decimal("1.01"))
        supply_to = _q(resistance * Decimal("1.02"))
        demand_from = _q(support * Decimal("0.99"))
        demand_to = _q(support * Decimal("1.005"))

        candles = quote.get("candles") or []
        marker_time = int(candles[len(candles) // 2].open_time) if candles else None

        pair = _pair_label(symbol)
        reasoning = (
            f"{pair} printed a clear {structure} after reclaiming structure near {_money(support)}. "
            f"Price is holding around {_money(close)} with "
            f"{'rising' if bullish else 'fading'} momentum, favoring a move toward {_money(take_profit)} "
            f"while invalidation remains near {_money(stop_loss)}."
        )

        overlays = _build_overlays(
            close=close,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            resistance=resistance,
            support=support,
            supply_from=supply_from,
            supply_to=supply_to,
            demand_from=demand_from,
            demand_to=demand_to,
            marker_time=marker_time,
        )
        # strip helper
        overlays.pop("_close", None)

        return {
            "trend": trend,
            "structure": structure,
            "structure_note": structure_note,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": f"1 : {rr}",
            "risk_reward_probability": probability,
            "confidence": confidence,
            "reasoning": reasoning,
            "resistance_range": f"{_money(supply_from)} – {_money(supply_to)}",
            "resistance_strength": 78 if bullish else 70,
            "support_range": f"{_money(demand_from)} – {_money(demand_to)}",
            "support_strength": 86 if bullish else 72,
            "overlays": overlays,
        }

    def _to_out(self, row: AiAnalysis) -> AnalysisOut:
        symbol = row.symbol
        meta = WorkspaceMetaOut(
            pair=_pair_label(symbol),
            symbol=symbol,
            timeframe=row.timeframe,
            exchange=row.exchange,
            open=_money(row.open_price),
            high=_money(row.high_price),
            low=_money(row.low_price),
            close=_money(row.close_price),
            change_percent=row.change_percent,
            volume=row.volume_label,
            ai_zones=row.ai_zones_label,
        )
        signal = AiSignalPanelOut(
            badge=row.model,
            trend={"label": "TREND", "value": row.trend},
            market_structure={
                "label": "MARKET STRUCTURE",
                "value": row.structure,
                "note": row.structure_note,
            },
            supply_demand={
                "resistance": SupplyDemandOut(
                    label=row.resistance_label,
                    range=row.resistance_range,
                    strength=row.resistance_strength,
                ),
                "support": SupplyDemandOut(
                    label=row.support_label,
                    range=row.support_range,
                    strength=row.support_strength,
                ),
            },
            risk_reward={
                "label": "RISK / REWARD PROBABILITY",
                "ratio": row.risk_reward_ratio,
                "probability": row.risk_reward_probability,
            },
            reasoning={"title": row.reasoning_title, "text": row.reasoning},
        )
        return AnalysisOut(
            id=row.id,
            symbol=row.symbol,
            timeframe=row.timeframe,
            exchange=row.exchange,
            model=row.model,
            lookback=row.lookback,
            trend=row.trend,
            structure=row.structure,
            confidence=row.confidence,
            is_saved=row.is_saved,
            entry=row.entry,
            stop_loss=row.stop_loss,
            take_profit=row.take_profit,
            risk_reward_ratio=row.risk_reward_ratio,
            created_at=row.created_at,
            meta=meta,
            trade_metrics=TradeMetricsOut(
                entry=_money(row.entry),
                stop_loss=_money(row.stop_loss),
                take_profit=_money(row.take_profit),
                entry_raw=row.entry,
                stop_loss_raw=row.stop_loss,
                take_profit_raw=row.take_profit,
            ),
            signal=signal,
            overlays=row.overlays or {},
        )

    async def generate(self, user_id: UUID, payload: GenerateAnalysisRequest) -> AnalysisOut:
        symbol = _normalize_symbol(payload.symbol)
        if payload.timeframe not in ALLOWED_TIMEFRAMES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timeframe")

        quote = await self._resolve_quote(symbol, payload.timeframe, payload.lookback)
        synth = self._synthesize(symbol, quote)

        row = AiAnalysis(
            user_id=user_id,
            symbol=symbol,
            timeframe=payload.timeframe,
            exchange="Binance",
            model="PRO MODEL",
            lookback=payload.lookback,
            open_price=quote["open"],
            high_price=quote["high"],
            low_price=quote["low"],
            close_price=quote["close"],
            change_percent=quote["change_percent"],
            volume_label=quote["volume_label"],
            ai_zones_label="Supply / Demand Active",
            trend=synth["trend"],
            structure=synth["structure"],
            structure_note=synth["structure_note"],
            resistance_range=synth["resistance_range"],
            resistance_strength=synth["resistance_strength"],
            support_range=synth["support_range"],
            support_strength=synth["support_strength"],
            risk_reward_ratio=synth["risk_reward_ratio"],
            risk_reward_probability=synth["risk_reward_probability"],
            confidence=synth["confidence"],
            reasoning=synth["reasoning"],
            entry=synth["entry"],
            stop_loss=synth["stop_loss"],
            take_profit=synth["take_profit"],
            overlays=synth["overlays"],
            is_saved=payload.save,
        )
        await self.repo.add(row)
        await self.repo.flush()
        return self._to_out(row)

    async def get_workspace(
        self,
        user_id: UUID,
        symbol: str,
        timeframe: str,
        lookback: int = 200,
        auto_generate: bool = True,
    ) -> WorkspaceOut:
        symbol = _normalize_symbol(symbol)
        if timeframe not in ALLOWED_TIMEFRAMES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timeframe")

        analysis_row = await self.repo.latest_for_symbol(user_id, symbol, timeframe)
        if analysis_row is None and auto_generate:
            analysis = await self.generate(
                user_id,
                GenerateAnalysisRequest(symbol=symbol, timeframe=timeframe, lookback=lookback),
            )
        elif analysis_row is not None:
            analysis = self._to_out(analysis_row)
        else:
            analysis = None

        candles = await self.repo.list_candles(symbol, timeframe, lookback)
        candle_payload = [
            {
                "time": int(c.open_time),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume or 0),
            }
            for c in candles
        ]

        return WorkspaceOut(
            symbols=SYMBOLS,
            timeframes=TIMEFRAMES,
            layouts=LAYOUTS,
            analysis=analysis,
            candles=candle_payload,
        )

    async def list_analyses(
        self,
        user_id: UUID,
        *,
        saved_only: bool = False,
        symbol: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AnalysisListOut:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_for_user(
            user_id,
            saved_only=saved_only,
            symbol=_normalize_symbol(symbol) if symbol else None,
            limit=page_size,
            offset=offset,
        )
        return AnalysisListOut(
            total=total,
            items=[
                AnalysisListItemOut(
                    id=r.id,
                    symbol=r.symbol,
                    timeframe=r.timeframe,
                    trend=r.trend,
                    confidence=r.confidence,
                    is_saved=r.is_saved,
                    entry=r.entry,
                    stop_loss=r.stop_loss,
                    take_profit=r.take_profit,
                    created_at=r.created_at,
                )
                for r in rows
            ],
        )

    async def get_analysis(self, user_id: UUID, analysis_id: UUID) -> AnalysisOut:
        row = await self.repo.get(user_id, analysis_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        return self._to_out(row)

    async def save_analysis(self, user_id: UUID, analysis_id: UUID) -> AnalysisOut:
        row = await self.repo.get(user_id, analysis_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        row.is_saved = True
        return self._to_out(row)

    async def delete_analysis(self, user_id: UUID, analysis_id: UUID) -> dict[str, str]:
        row = await self.repo.get(user_id, analysis_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        await self.repo.delete(row)
        return {"status": "deleted"}

    async def alert_draft(self, user_id: UUID, analysis_id: UUID) -> AlertDraftOut:
        row = await self.repo.get(user_id, analysis_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        return AlertDraftOut(
            symbol=row.symbol,
            source_analysis_id=row.id,
            message=f"Alert draft from {row.trend} {row.symbol} {row.timeframe} analysis",
            conditions=[
                {"type": "price_above", "price": float(row.entry), "label": "Entry"},
                {"type": "price_below", "price": float(row.stop_loss), "label": "Stop Loss"},
                {"type": "price_above", "price": float(row.take_profit), "label": "Take Profit"},
            ],
        )
