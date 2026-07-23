from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import (
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperPosition,
    PaperPositionEvent,
    PaperSentinelSuggestion,
)
from app.repositories.paper_repository import PaperRepository
from app.schemas.paper import (
    AskAiOut,
    AskAiRequest,
    EquityCurveOut,
    EquityPointOut,
    PaperDeskOut,
    PaperMetricOut,
    PaperPositionOut,
    PendingOrderOut,
    PlaceOrderOut,
    PlaceOrderRequest,
    PositionDetailOut,
    SentinelSuggestionOut,
    TimelineEventOut,
    TradeHistoryOut,
    TradePreviewOut,
)

FALLBACK_PRICES: dict[str, Decimal] = {
    "BTCUSDT": Decimal("64820.40"),
    "ETHUSDT": Decimal("3421.18"),
    "SOLUSDT": Decimal("152.80"),
    "LINKUSDT": Decimal("14.70"),
}

BASE_SYMBOLS = [
    {"value": "BTCUSDT", "label": "BTC/USDT"},
    {"value": "ETHUSDT", "label": "ETH/USDT"},
    {"value": "SOLUSDT", "label": "SOL/USDT"},
]

ASK_AI_ANSWERS = {
    "losing": "Price is testing your invalidation. Unrealized loss is within planned risk; cut only if structure breaks.",
    "tp": "TP sits beyond the next liquidity pool. Momentum stalled; a staged exit would have captured more.",
    "avoid": "Entry was slightly late after the impulse. Waiting for a pullback into demand would improve R:R.",
    "entry": "Better entry: limit at demand mid (prior swing low + ATR buffer).",
    "sl": "Widen SL below true structure low, or reduce size so risk % stays constant.",
}

DEFAULT_STARTING_EQUITY = Decimal("1000000.00")


def _q(value: Decimal, places: str = "0.01") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace("/", "").replace("-", "").replace(" ", "")


def _display_symbol(symbol: str) -> str:
    s = _normalize_symbol(symbol)
    if s.endswith("USDT") and len(s) > 4:
        return f"{s[:-4]}/USDT"
    return s


def _base_asset(symbol: str) -> str:
    s = _normalize_symbol(symbol)
    return s[:-4] if s.endswith("USDT") else s


def _size_label(size: Decimal, symbol: str) -> str:
    base = _base_asset(symbol)
    text = f"{size.normalize():f}".rstrip("0").rstrip(".")
    if "." not in text:
        text = f"{text}.000"
    return f"{text} {base}"


def _relative_time(dt: datetime | None) -> str:
    if dt is None:
        return ""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = int((now - dt).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    days = seconds // 86400
    if days == 1:
        return "Yesterday"
    return f"{days} days ago"


def _unrealized_pnl(side: str, entry: Decimal, current: Decimal, size: Decimal) -> Decimal:
    if side == "long":
        return _q((current - entry) * size)
    return _q((entry - current) * size)


def _health_and_lifecycle(
    side: str,
    entry: Decimal,
    current: Decimal,
    stop_loss: Decimal | None,
    take_profit: Decimal | None,
) -> tuple[str, str]:
    health = "healthy"
    lifecycle = "monitoring"

    if stop_loss is not None and stop_loss > 0:
        if side == "long":
            dist = abs(entry - stop_loss)
            if dist > 0 and current <= entry - dist * Decimal("0.85"):
                health = "near_sl"
        else:
            dist = abs(stop_loss - entry)
            if dist > 0 and current >= entry + dist * Decimal("0.85"):
                health = "near_sl"

    if take_profit is not None and take_profit > 0:
        if side == "long":
            dist = abs(take_profit - entry)
            if dist > 0 and current >= entry + dist * Decimal("0.85"):
                health = "near_tp"
                lifecycle = "near_tp"
        else:
            dist = abs(entry - take_profit)
            if dist > 0 and current <= entry - dist * Decimal("0.85"):
                health = "near_tp"
                lifecycle = "near_tp"

    pnl_pct = abs((current - entry) / entry) if entry else Decimal(0)
    if health == "healthy" and pnl_pct > Decimal("0.02"):
        if (side == "long" and current < entry) or (side == "short" and current > entry):
            health = "watch"

    return health, lifecycle


class PaperTradingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PaperRepository(session)

    async def ensure_account(self, user_id: UUID) -> PaperAccount:
        account = await self.repo.get_account_by_user(user_id)
        if account is not None:
            return account
        account = PaperAccount(
            user_id=user_id,
            cash=DEFAULT_STARTING_EQUITY,
            equity=DEFAULT_STARTING_EQUITY,
            starting_equity=DEFAULT_STARTING_EQUITY,
            win_rate_percent=Decimal("0"),
            total_pnl=Decimal("0"),
            max_drawdown_percent=Decimal("0"),
            learning_mode="practice",
            fee_rate_bps=10,
        )
        await self.repo.add(account)
        await self.repo.flush()
        return account

    async def _mark_price(self, symbol: str) -> Decimal:
        key = _normalize_symbol(symbol)
        price = await self.repo.get_asset_price(key)
        if price is not None:
            return price
        if key in FALLBACK_PRICES:
            return FALLBACK_PRICES[key]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown symbol: {symbol}")

    def _resolve_quantity(
        self,
        account: PaperAccount,
        size: Decimal,
        size_mode: str,
        entry: Decimal,
        stop_loss: Decimal | None,
    ) -> Decimal:
        if size_mode == "fixed":
            return size
        if size_mode == "percent":
            notional = account.equity * (size / Decimal("100"))
            return _q(notional / entry, "0.00000001")
        if size_mode == "risk":
            if stop_loss is None or stop_loss == entry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Risk-based sizing requires a valid stop_loss",
                )
            risk_cash = account.equity * (size / Decimal("100"))
            per_unit = abs(entry - stop_loss)
            if per_unit <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stop distance")
            return _q(risk_cash / per_unit, "0.00000001")
        if size_mode == "ai":
            # AI suggested: treat size as % portfolio with 0.5x of given or default 1%
            pct = size if size <= 5 else Decimal("1")
            notional = account.equity * (pct / Decimal("100"))
            return _q(notional / entry, "0.00000001")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid size_mode")

    def _default_sl_tp(self, side: str, entry: Decimal) -> tuple[Decimal, Decimal]:
        if side == "long":
            return _q(entry * Decimal("0.98"), "0.00000001"), _q(entry * Decimal("1.05"), "0.00000001")
        return _q(entry * Decimal("1.02"), "0.00000001"), _q(entry * Decimal("0.95"), "0.00000001")

    async def _refresh_marks(self, account: PaperAccount) -> None:
        positions = await self.repo.list_open_positions(account.id)
        unrealized = Decimal("0")
        for pos in positions:
            mark = await self._mark_price(pos.symbol)
            pos.current = mark
            pos.unrealized_pnl = _unrealized_pnl(pos.side, pos.entry, mark, pos.size)
            pos.health, pos.lifecycle = _health_and_lifecycle(
                pos.side, pos.entry, mark, pos.stop_loss, pos.take_profit
            )
            unrealized += pos.unrealized_pnl
        account.equity = _q(account.cash + unrealized)

    def _to_position_out(self, pos: PaperPosition) -> PaperPositionOut:
        return PaperPositionOut(
            id=pos.id,
            symbol=_display_symbol(pos.symbol),
            side=pos.side,
            size=pos.size,
            size_label=pos.size_label or _size_label(pos.size, pos.symbol),
            entry=pos.entry,
            current=pos.current,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            unrealized_pnl=pos.unrealized_pnl,
            health=pos.health,
            lifecycle=pos.lifecycle,
            opened_at=_relative_time(pos.opened_at),
            notes=pos.notes,
        )

    async def get_desk(self, user_id: UUID) -> PaperDeskOut:
        account = await self.ensure_account(user_id)
        await self._refresh_marks(account)

        open_positions = await self.repo.list_open_positions(account.id)
        pending = await self.repo.list_pending_orders(account.id)
        closed = await self.repo.list_closed_positions(account.id, limit=20)
        sentinel = await self.repo.get_sentinel(account.id)

        change_pct = Decimal("0")
        if account.starting_equity > 0:
            change_pct = _q(((account.equity - account.starting_equity) / account.starting_equity) * 100)

        metrics = [
            PaperMetricOut(
                id="equity",
                label="PAPER EQUITY",
                value=f"${account.equity:,.2f}",
                meta=f"{change_pct:+.1f}% vs start",
                tone="success" if change_pct >= 0 else "danger",
            ),
            PaperMetricOut(
                id="winrate",
                label="WIN RATE",
                value=f"{account.win_rate_percent}%",
                meta="Closed trades",
                tone="default",
                progress=float(account.win_rate_percent),
            ),
            PaperMetricOut(
                id="pnl",
                label="TOTAL PNL",
                value=f"{account.total_pnl:+,.2f}",
                meta="Realized",
                tone="success" if account.total_pnl >= 0 else "danger",
            ),
            PaperMetricOut(
                id="drawdown",
                label="MAX DRAWDOWN",
                value=f"-{abs(account.max_drawdown_percent):.2f}%",
                meta="Peak to Trough",
                tone="danger",
            ),
        ]

        return PaperDeskOut(
            learning_mode=account.learning_mode,
            metrics=metrics,
            open_positions=[self._to_position_out(p) for p in open_positions],
            pending_orders=[
                PendingOrderOut(
                    id=o.id,
                    symbol=_display_symbol(o.symbol),
                    side=o.side,
                    type=o.order_type,
                    size_label=o.size_label or _size_label(o.size, o.symbol),
                    limit_price=o.limit_price or Decimal("0"),
                    stop_loss=o.stop_loss,
                    take_profit=o.take_profit,
                    created_at=_relative_time(o.created_at),
                )
                for o in pending
            ],
            trade_history=[
                TradeHistoryOut(
                    id=p.id,
                    symbol=_display_symbol(p.symbol),
                    side=p.side,
                    size_label=p.size_label or _size_label(p.size, p.symbol),
                    entry=p.entry,
                    exit=p.exit_price or p.current,
                    pnl=p.realized_pnl,
                    closed_at=_relative_time(p.closed_at),
                    lifecycle="closed",
                )
                for p in closed
            ],
            sentinel=(
                SentinelSuggestionOut(
                    id=sentinel.id,
                    message=sentinel.message,
                    symbol=_display_symbol(sentinel.symbol),
                    suggested_tp=sentinel.suggested_tp,
                )
                if sentinel
                else None
            ),
            symbols=BASE_SYMBOLS,
        )

    async def get_equity(self, user_id: UUID, range_key: str) -> EquityCurveOut:
        if range_key not in {"1D", "1W", "1M", "ALL"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid range")
        account = await self.ensure_account(user_id)
        points = await self.repo.list_equity_points(account.id, range_key)
        if not points:
            # live fallback: single point at current equity (scaled like UI millions)
            scaled = _q(account.equity / Decimal("1000000"), "0.001")
            return EquityCurveOut(range=range_key, points=[EquityPointOut(label="Now", value=scaled)])
        return EquityCurveOut(
            range=range_key,
            points=[EquityPointOut(label=p.label, value=p.value) for p in points],
        )

    async def preview_order(self, user_id: UUID, payload: PlaceOrderRequest) -> TradePreviewOut:
        account = await self.ensure_account(user_id)
        symbol = _normalize_symbol(payload.symbol)
        mark = await self._mark_price(symbol)
        entry = payload.limit_price if payload.order_type == "limit" and payload.limit_price else mark

        stop_loss, take_profit = payload.stop_loss, payload.take_profit
        if payload.use_ai_sl_tp or stop_loss is None or take_profit is None:
            ai_sl, ai_tp = self._default_sl_tp(payload.side, entry)
            stop_loss = stop_loss or ai_sl
            take_profit = take_profit or ai_tp

        qty = self._resolve_quantity(account, payload.size, payload.size_mode, entry, stop_loss)
        notional = qty * entry
        fee = _q(notional * Decimal(account.fee_rate_bps) / Decimal("10000"))

        risk_pct = Decimal("0")
        if stop_loss is not None and account.equity > 0:
            risk_cash = abs(entry - stop_loss) * qty
            risk_pct = _q((risk_cash / account.equity) * 100)

        rr = "n/a"
        if stop_loss is not None and take_profit is not None and abs(entry - stop_loss) > 0:
            reward = abs(take_profit - entry)
            risk = abs(entry - stop_loss)
            rr = f"1:{_q(reward / risk, '0.01')}"

        risk_level = "low"
        if risk_pct >= 3:
            risk_level = "extreme"
        elif risk_pct >= 2:
            risk_level = "high"
        elif risk_pct >= 1:
            risk_level = "medium"

        warnings: list[dict[str, str]] = []
        if risk_pct >= 1.5:
            warnings.append(
                {"id": "risk", "title": "Elevated risk", "detail": f"This idea risks {risk_pct}% of paper equity."}
            )
        open_pos = await self.repo.list_open_positions(account.id)
        if any(_normalize_symbol(p.symbol) == symbol for p in open_pos):
            warnings.append(
                {
                    "id": "corr",
                    "title": "Existing exposure",
                    "detail": f"You already hold an open {_display_symbol(symbol)} position.",
                }
            )

        return TradePreviewOut(
            symbol=_display_symbol(symbol),
            side=payload.side,
            entry_price=entry,
            position_size=_size_label(qty, symbol),
            quantity=qty,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_percent=risk_pct,
            risk_reward=rr,
            estimated_fees=f"${fee:,.2f}",
            ai_confidence=78 if account.learning_mode != "exam" else 0,
            holding_time="Intraday–swing",
            explanations=[
                {"id": "1", "text": "Trend context checked"},
                {"id": "2", "text": "Risk sized vs equity"},
                {"id": "3", "text": "SL/TP structure aligned"},
                {"id": "4", "text": "Fees estimated"},
                {"id": "5", "text": "Risk acceptable" if risk_pct < 2 else "Risk elevated"},
            ],
            warnings=warnings,
            risk_level=risk_level,
        )

    async def place_order(self, user_id: UUID, payload: PlaceOrderRequest) -> PlaceOrderOut:
        account = await self.ensure_account(user_id)
        await self._refresh_marks(account)

        symbol = _normalize_symbol(payload.symbol)
        mark = await self._mark_price(symbol)

        if payload.order_type == "limit" and payload.limit_price is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit_price required for limit orders")

        entry = payload.limit_price if payload.order_type == "limit" else mark
        stop_loss, take_profit = payload.stop_loss, payload.take_profit
        if payload.use_ai_sl_tp or stop_loss is None or take_profit is None:
            ai_sl, ai_tp = self._default_sl_tp(payload.side, entry)  # type: ignore[arg-type]
            stop_loss = stop_loss or ai_sl
            take_profit = take_profit or ai_tp

        qty = self._resolve_quantity(account, payload.size, payload.size_mode, entry, stop_loss)  # type: ignore[arg-type]
        if qty <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resolved size must be > 0")

        order = PaperOrder(
            account_id=account.id,
            symbol=symbol,
            side=payload.side,
            order_type=payload.order_type,
            size=qty,
            size_label=_size_label(qty, symbol),
            limit_price=payload.limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            size_mode=payload.size_mode,
            status="pending",
        )
        await self.repo.add(order)
        await self.repo.flush()

        if payload.order_type == "limit":
            # Keep pending until cancelled or price crosses (checked on desk refresh)
            return PlaceOrderOut(order_id=order.id, status="pending", message="Limit order resting")

        position = await self._fill_market(account, order, mark)
        return PlaceOrderOut(
            order_id=order.id,
            status="filled",
            position_id=position.id,
            message="Market order filled",
        )

    async def _fill_market(self, account: PaperAccount, order: PaperOrder, fill_price: Decimal) -> PaperPosition:
        notional = order.size * fill_price
        fee = _q(notional * Decimal(account.fee_rate_bps) / Decimal("10000"), "0.00000001")
        # Margin sim: reserve notional for long; short still reserves notional from cash
        if account.cash < notional + fee:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient paper cash")

        account.cash = _q(account.cash - notional - fee)
        health, lifecycle = _health_and_lifecycle(
            order.side, fill_price, fill_price, order.stop_loss, order.take_profit
        )
        lifecycle = "opened"

        position = PaperPosition(
            account_id=account.id,
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            size=order.size,
            size_label=order.size_label,
            entry=fill_price,
            current=fill_price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            health=health,
            lifecycle=lifecycle,
            status="open",
            notes=None,
            ai_analysis="Paper fill executed by simulator.",
            future_commentary="Monitor structure; trail if momentum continues.",
            chart_snapshot_label=f"{_display_symbol(order.symbol)} · Paper entry",
            risk_changes=[{"id": "r1", "label": "Initial risk", "value": "planned"}],
            trade_events=[
                {"id": "e1", "label": "Fill", "value": f"{'Buy' if order.side == 'long' else 'Sell'} {order.size_label}"},
                {"id": "e2", "label": "SL set", "value": str(order.stop_loss or "—")},
                {"id": "e3", "label": "TP set", "value": str(order.take_profit or "—")},
            ],
            execution_history=[
                {
                    "id": "x1",
                    "label": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                    "value": f"{'BUY' if order.side == 'long' else 'SELL'} {order.size} @ {fill_price}",
                },
                {"id": "x2", "label": "Fees", "value": f"${fee:,.2f}"},
            ],
        )
        await self.repo.add(position)
        await self.repo.flush()

        fill = PaperFill(
            account_id=account.id,
            order_id=order.id,
            position_id=position.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.size,
            price=fill_price,
            fee=fee,
        )
        await self.repo.add(fill)

        event = PaperPositionEvent(
            position_id=position.id,
            time_label=datetime.now(timezone.utc).strftime("%H:%M"),
            title="Opened",
            detail=f"Market {order.side} filled at {fill_price}",
            sort_order=0,
        )
        await self.repo.add(event)

        order.status = "filled"
        await self._refresh_marks(account)
        return position

    async def match_pending_limits(self, user_id: UUID) -> int:
        """Fill resting limits when mark crosses limit price."""
        account = await self.ensure_account(user_id)
        pending = await self.repo.list_pending_orders(account.id)
        filled = 0
        for order in pending:
            if order.order_type != "limit" or order.limit_price is None:
                continue
            mark = await self._mark_price(order.symbol)
            hit = False
            if order.side == "long" and mark <= order.limit_price:
                hit = True
            if order.side == "short" and mark >= order.limit_price:
                hit = True
            if hit:
                await self._fill_market(account, order, order.limit_price)
                filled += 1
        return filled

    async def cancel_order(self, user_id: UUID, order_id: UUID) -> PlaceOrderOut:
        account = await self.ensure_account(user_id)
        order = await self.repo.get_order(account.id, order_id)
        if order is None or order.status != "pending":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending order not found")
        order.status = "cancelled"
        return PlaceOrderOut(order_id=order.id, status="cancelled", message="Order cancelled")

    async def close_position(self, user_id: UUID, position_id: UUID) -> PlaceOrderOut:
        account = await self.ensure_account(user_id)
        await self._refresh_marks(account)
        position = await self.repo.get_position(account.id, position_id)
        if position is None or position.status != "open":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open position not found")

        mark = await self._mark_price(position.symbol)
        pnl = _unrealized_pnl(position.side, position.entry, mark, position.size)
        notional = position.size * mark
        fee = _q(notional * Decimal(account.fee_rate_bps) / Decimal("10000"))
        # Return reserved notional + pnl - exit fee
        entry_notional = position.size * position.entry
        account.cash = _q(account.cash + entry_notional + pnl - fee)
        account.total_pnl = _q(account.total_pnl + pnl - fee)

        position.current = mark
        position.exit_price = mark
        position.realized_pnl = _q(pnl - fee)
        position.unrealized_pnl = Decimal("0")
        position.status = "closed"
        position.lifecycle = "closed"
        position.closed_at = datetime.now(timezone.utc)

        closed = await self.repo.list_closed_positions(account.id, limit=500)
        wins = sum(1 for p in closed if p.realized_pnl > 0)
        if closed:
            account.win_rate_percent = _q(Decimal(wins) / Decimal(len(closed)) * 100)

        peak = max(account.starting_equity, account.equity)
        await self._refresh_marks(account)
        if peak > 0 and account.equity < peak:
            dd = _q(((peak - account.equity) / peak) * 100, "0.0001")
            if dd > account.max_drawdown_percent:
                account.max_drawdown_percent = dd

        await self.repo.add(
            PaperPositionEvent(
                position_id=position.id,
                time_label=datetime.now(timezone.utc).strftime("%H:%M"),
                title="Closed",
                detail=f"Closed at {mark} · PnL {position.realized_pnl}",
                sort_order=99,
            )
        )

        return PlaceOrderOut(
            order_id=position.order_id or position.id,
            status="closed",
            position_id=position.id,
            message=f"Position closed · PnL {position.realized_pnl}",
        )

    async def get_position_detail(self, user_id: UUID, position_id: UUID) -> PositionDetailOut:
        account = await self.ensure_account(user_id)
        await self._refresh_marks(account)
        position = await self.repo.get_position(account.id, position_id)
        if position is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        events = await self.repo.list_position_events(position.id)
        return PositionDetailOut(
            position=self._to_position_out(position),
            timeline=[
                TimelineEventOut(id=e.id, time=e.time_label, title=e.title, detail=e.detail) for e in events
            ],
            risk_changes=list(position.risk_changes or []),
            trade_events=list(position.trade_events or []),
            execution_history=list(position.execution_history or []),
            ai_analysis=position.ai_analysis,
            future_commentary=position.future_commentary,
            chart_snapshot_label=position.chart_snapshot_label,
        )

    async def set_learning_mode(self, user_id: UUID, mode: str) -> dict[str, str]:
        account = await self.ensure_account(user_id)
        account.learning_mode = mode
        return {"mode": mode}

    async def ask_ai(self, user_id: UUID, payload: AskAiRequest) -> AskAiOut:
        account = await self.ensure_account(user_id)
        answer = ASK_AI_ANSWERS.get(payload.prompt_id, "No guidance available for this prompt.")
        exam_score = None
        exam_summary = None
        if account.learning_mode == "exam":
            exam_score = 78
            exam_summary = "Execution solid. Risk sizing slightly aggressive vs daily limit."
        return AskAiOut(
            prompt_id=payload.prompt_id,
            answer=answer,
            exam_score=exam_score,
            exam_summary=exam_summary,
        )

    async def sentinel_action(self, user_id: UUID, action: str) -> dict[str, str]:
        account = await self.ensure_account(user_id)
        sentinel = await self.repo.get_sentinel(account.id)
        if sentinel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active sentinel suggestion")

        if action == "ignore":
            sentinel.is_active = False
            return {"status": "ignored"}

        # apply: update open position TP matching symbol
        positions = await self.repo.list_open_positions(account.id)
        target = _normalize_symbol(sentinel.symbol)
        for pos in positions:
            if _normalize_symbol(pos.symbol) == target and sentinel.suggested_tp is not None:
                pos.take_profit = sentinel.suggested_tp
                pos.lifecycle = "monitoring"
                break
        sentinel.is_active = False
        return {"status": "applied"}
