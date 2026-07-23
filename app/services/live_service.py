from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.live import (
    LiveAccount,
    LiveActivityEvent,
    LiveBalance,
    LiveEmergencyEvent,
    LiveGuardianAlert,
    LiveOrder,
    LivePosition,
)
from app.repositories.live_repository import LiveRepository
from app.schemas.live import (
    AskAiOut,
    AskAiRequest,
    EmergencyStopOut,
    EmergencyStopRequest,
    GuardianAlertOut,
    LiveActivityOut,
    LiveBalanceOut,
    LiveDeskOut,
    LiveOrderOut,
    LivePositionOut,
    LiveSettingsRequest,
    PlaceLiveOrderOut,
    PlaceLiveOrderRequest,
    PositionActionRequest,
    PositionDetailOut,
    SetAutoTradingRequest,
    TradePreviewOut,
)

FALLBACK_PRICES = {
    "BTCUSDT": Decimal("65890.40"),
    "ETHUSDT": Decimal("3521.80"),
    "SOLUSDT": Decimal("152.60"),
    "LINKUSDT": Decimal("14.62"),
    "DOTUSDT": Decimal("7.55"),
}

EMERGENCY_ACTIONS = [
    {"id": "close_all", "label": "Close All Positions", "description": "Market-close every open live position immediately."},
    {"id": "cancel_all", "label": "Cancel All Orders", "description": "Cancel every pending order on the connected exchange."},
    {"id": "disable_auto", "label": "Disable Auto Trading", "description": "Turn off automated strategy execution."},
    {"id": "lock", "label": "Lock Trading", "description": "Block new orders until manually unlocked."},
    {"id": "risk_only", "label": "Risk Only Mode", "description": "Allow exits and risk reductions only — no new entries."},
]

BOTTOM_PRIMARY = [
    {"id": "quick_buy", "label": "Quick Buy Market", "tone": "buy"},
    {"id": "quick_sell", "label": "Quick Sell Market", "tone": "sell"},
]

BOTTOM_TOOLS = [
    {"id": "close", "label": "Close"},
    {"id": "reverse", "label": "Reverse"},
    {"id": "partial", "label": "Partial Close"},
    {"id": "breakeven", "label": "Breakeven"},
    {"id": "trail", "label": "Trailing Stop"},
    {"id": "pos_calc", "label": "Pos Calc"},
    {"id": "risk_calc", "label": "Risk Calc"},
    {"id": "templates", "label": "Templates"},
]

AI_PROMPTS = [
    {"id": "explain", "label": "Explain current positions"},
    {"id": "losses", "label": "Explain losses"},
    {"id": "profits", "label": "Explain profits"},
    {"id": "exits", "label": "Recommend exits"},
    {"id": "entries", "label": "Recommend entries"},
    {"id": "leverage", "label": "Optimize leverage"},
    {"id": "sl", "label": "Optimize Stop Loss"},
    {"id": "tp", "label": "Optimize Take Profit"},
]

AI_REPLIES = {
    "explain": "You are net long majors with healthy BTC, SOL near TP, ETH short under pressure, and LINK near SL.",
    "losses": "ETH and LINK are within planned risk. Cut LINK if structure fails; manage ETH size.",
    "profits": "BTC and SOL carry the book. Protect SOL with partial TP and trail BTC.",
    "exits": "Partial SOL now; tighten ETH; hold BTC while above 64,800.",
    "entries": "No new longs until daily risk < 1.2%. Prefer pullback entries only.",
    "leverage": "Account leverage is elevated vs vol — target lower leverage on new entries.",
    "sl": "Move BTC SL to breakeven after +1R; ETH SL tighter if holding.",
    "tp": "SOL: scale at TP; BTC: leave runner to planned target.",
}

DEFAULT_RISK = {
    "max_daily_loss": "$2,500.00",
    "max_daily_loss_progress": 42,
    "position_limits": "4/10",
    "daily_margin_used": "$12,450.00",
    "max_drawdown": "2.4%",
    "account_leverage": "10.5x",
}

DEFAULT_EXPOSURE = {
    "long_exposure": "62%",
    "short_exposure": "38%",
    "sector_exposure": "Crypto majors 78%",
    "asset_allocation": "BTC 44% · ETH 31% · Alts 25%",
    "correlation": "0.72 BTC–SOL",
    "available_margin": "$41,820",
    "used_margin": "$12,450",
    "daily_risk": "1.8%",
    "max_daily_loss": "$2,500",
}

DEFAULT_STATUS = [
    {"id": "exchange", "label": "Exchange", "status": "online", "meta": "Binance"},
    {"id": "ws", "label": "WebSocket", "status": "online", "meta": "42ms"},
    {"id": "latency", "label": "Latency", "status": "online", "meta": "38ms"},
    {"id": "ai", "label": "AI Engine", "status": "online"},
    {"id": "trading", "label": "Trading Engine", "status": "online"},
    {"id": "risk", "label": "Risk Engine", "status": "online"},
    {"id": "market", "label": "Market Data", "status": "online"},
    {"id": "queue", "label": "Order Queue", "status": "online", "meta": "0 pending"},
]

DEFAULT_MONITOR = [
    {"id": "funding", "label": "Funding", "value": "0.012%", "tone": "default"},
    {"id": "oi", "label": "Open Interest", "value": "$18.4B", "tone": "default"},
    {"id": "fg", "label": "Fear & Greed", "value": "64", "tone": "success"},
    {"id": "whale", "label": "Whale Activity", "value": "Elevated", "tone": "warning"},
    {"id": "news", "label": "News Impact", "value": "Low", "tone": "default"},
    {"id": "econ", "label": "Econ Events", "value": "CPI in 2d", "tone": "warning"},
    {"id": "vol", "label": "Volatility", "value": "High", "tone": "danger"},
    {"id": "trend", "label": "Trend Strength", "value": "Bullish 72", "tone": "success"},
]

AI_APPROVAL = {
    "checks": [
        {"id": "trend", "label": "Trend", "status": "pass", "value": "Bullish"},
        {"id": "structure", "label": "Market Structure", "status": "pass", "value": "Confirmed"},
        {"id": "vol", "label": "Volatility", "status": "warn", "value": "High"},
        {"id": "news", "label": "News Risk", "status": "warn", "value": "Medium"},
    ],
    "confidence": 84,
    "recommendation": "Proceed with 0.5% account risk.",
}


def _d(v: float | int | str | Decimal) -> Decimal:
    return Decimal(str(v))


def _clock() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace("/", "").replace("-", "").replace(" ", "")


def _mark(symbol: str) -> Decimal:
    return FALLBACK_PRICES.get(_normalize_symbol(symbol), Decimal("100"))


def _type_label(order_type: str, side: str) -> str:
    base = {"market": "Market", "limit": "Limit", "stop": "Stop"}.get(order_type, order_type.title())
    direction = "Buy" if side == "long" else "Sell"
    if order_type == "stop":
        return "Stop Loss"
    return f"{base} {direction}"


class LiveTradingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LiveRepository(session)

    async def ensure_account(self, user_id: UUID) -> LiveAccount:
        account = await self.repo.get_account(user_id)
        if account is not None:
            return account
        account = LiveAccount(
            id=uuid4(),
            user_id=user_id,
            exchange="Binance",
            api_active=True,
            auto_trading=False,
            trading_locked=False,
            risk_only_mode=False,
            default_leverage=10,
            margin_type="cross",
            total_unrealized_pnl=_d(0),
            risk_controls=dict(DEFAULT_RISK),
            portfolio_exposure=dict(DEFAULT_EXPOSURE),
            system_status=list(DEFAULT_STATUS),
            market_monitor=list(DEFAULT_MONITOR),
        )
        await self.repo.add(account)
        await self.repo.flush()
        await self.session.commit()
        loaded = await self.repo.get_account(user_id)
        assert loaded is not None
        return loaded

    def _position_out(self, p: LivePosition) -> LivePositionOut:
        return LivePositionOut(
            id=p.id,
            symbol=p.symbol,
            side=p.side,
            size=p.size_label or str(p.size),
            entry=p.entry,
            mark=p.mark,
            leverage=p.leverage,
            unrealized_pnl=p.unrealized_pnl,
            health=p.health,
            stop_loss=p.stop_loss,
            take_profit=p.take_profit,
        )

    def _order_out(self, o: LiveOrder) -> LiveOrderOut:
        return LiveOrderOut(
            id=o.id,
            symbol=o.symbol,
            type_label=o.type_label,
            side=o.side,
            price=o.price,
            amount=o.amount_label or str(o.amount),
            filled_percent=o.filled_percent,
        )

    async def _add_activity(
        self,
        account_id: UUID,
        *,
        title: str,
        detail: str,
        category: str = "system",
        severity: str = "info",
    ) -> None:
        await self.repo.add(
            LiveActivityEvent(
                id=uuid4(),
                account_id=account_id,
                timestamp_label=_clock(),
                title=title,
                detail=detail,
                category=category,
                severity=severity,
            )
        )

    def _to_desk(self, account: LiveAccount) -> LiveDeskOut:
        open_positions = [p for p in (account.positions or []) if p.status == "open"]
        open_orders = [o for o in (account.orders or []) if o.status == "open"]
        activities = sorted(account.activities or [], key=lambda a: a.created_at, reverse=True)[:30]
        alerts = sorted(
            [g for g in (account.guardian_alerts or []) if g.active],
            key=lambda g: g.sort_order,
        )
        balances = sorted(account.balances or [], key=lambda b: b.sort_order)
        total_pnl = sum((p.unrealized_pnl for p in open_positions), _d(0))
        return LiveDeskOut(
            page_meta={
                "title": "Live Trading",
                "subtitle": "Institutional AI trading terminal — execution, risk, and capital protection.",
            },
            exchange=account.exchange,
            api_active=account.api_active,
            auto_trading=account.auto_trading,
            trading_locked=account.trading_locked,
            risk_only_mode=account.risk_only_mode,
            default_leverage=account.default_leverage,
            margin_type=account.margin_type,
            total_unrealized_pnl=total_pnl,
            risk_controls=account.risk_controls or dict(DEFAULT_RISK),
            balances=[
                LiveBalanceOut(id=b.id, asset=b.asset, amount=b.amount, change_24h=b.change_24h) for b in balances
            ],
            portfolio_exposure=account.portfolio_exposure or dict(DEFAULT_EXPOSURE),
            positions=[self._position_out(p) for p in open_positions],
            orders=[self._order_out(o) for o in open_orders],
            activity=[
                LiveActivityOut(
                    id=a.id,
                    timestamp=a.timestamp_label,
                    title=a.title,
                    detail=a.detail,
                    category=a.category,
                    severity=a.severity,
                )
                for a in activities
            ],
            guardian_alerts=[
                GuardianAlertOut(
                    id=g.id,
                    title=g.title,
                    detail=g.detail,
                    severity=g.severity,
                    action_label=g.action_label,
                )
                for g in alerts
            ],
            market_monitor=list(account.market_monitor or DEFAULT_MONITOR),
            system_status=list(account.system_status or DEFAULT_STATUS),
            emergency_actions=EMERGENCY_ACTIONS,
            bottom_bar_primary=BOTTOM_PRIMARY,
            bottom_bar_tools=BOTTOM_TOOLS,
            ai_assistant_prompts=AI_PROMPTS,
            ai_approval_defaults=AI_APPROVAL,
        )

    async def get_desk(self, user_id: UUID) -> LiveDeskOut:
        account = await self.ensure_account(user_id)
        return self._to_desk(account)

    async def get_position_detail(self, user_id: UUID, position_id: UUID) -> PositionDetailOut:
        account = await self.ensure_account(user_id)
        position = await self.repo.get_position(account.id, position_id)
        if position is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        detail = position.detail if isinstance(position.detail, dict) else {}
        return PositionDetailOut(
            position=self._position_out(position),
            timeline=list(detail.get("timeline") or []),
            ai_analysis=str(detail.get("ai_analysis") or "No AI analysis yet."),
            entry_reason=str(detail.get("entry_reason") or ""),
            current_risk=str(detail.get("current_risk") or ""),
            stop_loss_history=list(detail.get("stop_loss_history") or []),
            take_profit_history=list(detail.get("take_profit_history") or []),
            ai_suggestions=list(detail.get("ai_suggestions") or []),
            trade_events=list(detail.get("trade_events") or []),
            market_snapshot=str(detail.get("market_snapshot") or ""),
        )

    async def set_auto_trading(self, user_id: UUID, payload: SetAutoTradingRequest) -> LiveDeskOut:
        account = await self.ensure_account(user_id)
        if account.trading_locked and payload.enabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trading is locked")
        account.auto_trading = payload.enabled
        await self._add_activity(
            account.id,
            title="Auto Trading Updated",
            detail=f"Auto trading {'enabled' if payload.enabled else 'disabled'}.",
            category="system",
            severity="info",
        )
        await self.session.commit()
        loaded = await self.repo.get_account(user_id)
        assert loaded is not None
        return self._to_desk(loaded)

    async def update_settings(self, user_id: UUID, payload: LiveSettingsRequest) -> LiveDeskOut:
        account = await self.ensure_account(user_id)
        if payload.leverage is not None:
            account.default_leverage = payload.leverage
        if payload.margin_type is not None:
            account.margin_type = payload.margin_type
        await self.session.commit()
        loaded = await self.repo.get_account(user_id)
        assert loaded is not None
        return self._to_desk(loaded)

    def preview_order(self, account: LiveAccount, payload: PlaceLiveOrderRequest) -> TradePreviewOut:
        symbol = _normalize_symbol(payload.symbol)
        mark = payload.price or _mark(symbol)
        leverage = payload.leverage or account.default_leverage
        margin_type = payload.margin_type or account.margin_type
        side = payload.side
        liq = mark * (_d("0.91") if side == "long" else _d("1.10"))
        return TradePreviewOut(
            approval=dict(AI_APPROVAL),
            confirm={
                "asset": symbol,
                "direction": side,
                "entry_price": float(mark),
                "order_type": payload.order_type,
                "position_size": f"{payload.amount} {symbol.replace('USDT', '')}",
                "leverage": leverage,
                "margin_type": margin_type,
                "stop_loss": str(payload.stop_loss or (mark * _d("0.96") if side == "long" else mark * _d("1.04"))),
                "take_profit": str(payload.take_profit or (mark * _d("1.04") if side == "long" else mark * _d("0.96"))),
                "risk_percent": 0.5,
                "risk_reward": "1:2.1",
                "estimated_fees": f"${(payload.amount * mark * _d('0.0004')):.2f}",
                "liquidation_price": f"{liq:.2f}",
                "ai_confidence": AI_APPROVAL["confidence"],
            },
        )

    async def preview(self, user_id: UUID, payload: PlaceLiveOrderRequest) -> TradePreviewOut:
        account = await self.ensure_account(user_id)
        return self.preview_order(account, payload)

    async def place_order(self, user_id: UUID, payload: PlaceLiveOrderRequest) -> PlaceLiveOrderOut:
        account = await self.ensure_account(user_id)
        if account.trading_locked:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trading is locked")
        if account.risk_only_mode:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk-only mode blocks new entries")
        if not payload.confirm:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="confirm=true required")

        symbol = _normalize_symbol(payload.symbol)
        leverage = payload.leverage or account.default_leverage
        margin_type = payload.margin_type or account.margin_type
        mark = _mark(symbol)
        price = payload.price or mark

        if payload.order_type == "market":
            position = LivePosition(
                id=uuid4(),
                account_id=account.id,
                symbol=symbol,
                side=payload.side,
                size=payload.amount,
                size_label=str(payload.amount),
                entry=price,
                mark=mark,
                leverage=leverage,
                margin_type=margin_type,
                unrealized_pnl=_d(0),
                health="healthy",
                stop_loss=payload.stop_loss,
                take_profit=payload.take_profit,
                status="open",
                detail={
                    "timeline": [
                        {
                            "id": "t1",
                            "time": datetime.now(timezone.utc).strftime("%H:%M"),
                            "title": "Opened",
                            "detail": f"Market {payload.side} {payload.amount} @ {price}",
                        }
                    ],
                    "ai_analysis": "Simulated live fill. Monitor structure and guardian limits.",
                    "entry_reason": "Manual live desk entry.",
                    "current_risk": "0.5% account",
                    "stop_loss_history": [{"id": "s1", "label": "Current", "value": str(payload.stop_loss or "—")}],
                    "take_profit_history": [{"id": "p1", "label": "Current", "value": str(payload.take_profit or "—")}],
                    "ai_suggestions": ["Trail after +1R", "Keep size within daily risk"],
                    "trade_events": [{"id": "e1", "label": "Fill", "value": f"{payload.side.upper()} {payload.amount} @ {price}"}],
                    "market_snapshot": f"{symbol} · Simulated live · Lev {leverage}x",
                },
            )
            await self.repo.add(position)
            await self._add_activity(
                account.id,
                title="Order Filled",
                detail=f"{'Bought' if payload.side == 'long' else 'Sold'} {payload.amount} {symbol} @ {price}",
                category="order_filled",
                severity="success",
            )
            await self.session.commit()
            loaded = await self.repo.get_account(user_id)
            assert loaded is not None
            return PlaceLiveOrderOut(
                message="Market order filled (simulated)",
                order=None,
                position=self._position_out(position),
                desk=self._to_desk(loaded),
            )

        order = LiveOrder(
            id=uuid4(),
            account_id=account.id,
            symbol=symbol,
            side=payload.side,
            order_type=payload.order_type,
            type_label=_type_label(payload.order_type, payload.side),
            price=price,
            amount=payload.amount,
            amount_label=str(payload.amount),
            filled_percent=_d(0),
            leverage=leverage,
            margin_type=margin_type,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            status="open",
        )
        await self.repo.add(order)
        await self._add_activity(
            account.id,
            title="Order Placed",
            detail=f"{order.type_label} {symbol} placed successfully.",
            category="system",
            severity="success",
        )
        await self.session.commit()
        loaded = await self.repo.get_account(user_id)
        assert loaded is not None
        return PlaceLiveOrderOut(
            message="Order submitted (simulated)",
            order=self._order_out(order),
            position=None,
            desk=self._to_desk(loaded),
        )

    async def cancel_order(self, user_id: UUID, order_id: UUID) -> PlaceLiveOrderOut:
        account = await self.ensure_account(user_id)
        order = await self.repo.get_order(account.id, order_id)
        if order is None or order.status != "open":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open order not found")
        order.status = "cancelled"
        await self._add_activity(
            account.id,
            title="Order Cancelled",
            detail=f"Cancelled {order.type_label} {order.symbol}.",
            category="system",
            severity="info",
        )
        await self.session.commit()
        loaded = await self.repo.get_account(user_id)
        assert loaded is not None
        return PlaceLiveOrderOut(message="Order cancelled", order=self._order_out(order), desk=self._to_desk(loaded))

    async def cancel_all_orders(self, user_id: UUID) -> PlaceLiveOrderOut:
        account = await self.ensure_account(user_id)
        orders = await self.repo.list_open_orders(account.id)
        for order in orders:
            order.status = "cancelled"
        await self._add_activity(
            account.id,
            title="Cancel All Orders",
            detail=f"Cancelled {len(orders)} pending order(s).",
            category="system",
            severity="warning",
        )
        await self.session.commit()
        loaded = await self.repo.get_account(user_id)
        assert loaded is not None
        return PlaceLiveOrderOut(message=f"Cancelled {len(orders)} order(s)", desk=self._to_desk(loaded))

    async def position_action(
        self, user_id: UUID, position_id: UUID, payload: PositionActionRequest
    ) -> PlaceLiveOrderOut:
        account = await self.ensure_account(user_id)
        position = await self.repo.get_position(account.id, position_id)
        if position is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

        action = payload.action
        if action == "close":
            position.status = "closed"
            position.closed_at = datetime.now(timezone.utc)
            position.health = "closing"
            msg = f"Closed {position.symbol}"
        elif action == "partial":
            pct = payload.percent or _d(50)
            position.size = (position.size * (_d(100) - pct) / _d(100)).quantize(Decimal("0.00000001"))
            position.size_label = str(position.size)
            msg = f"Partial close {pct}% on {position.symbol}"
        elif action == "reverse":
            position.side = "short" if position.side == "long" else "long"
            position.entry = position.mark
            position.unrealized_pnl = _d(0)
            msg = f"Reversed {position.symbol} to {position.side}"
        elif action == "breakeven":
            position.stop_loss = position.entry
            msg = f"Stop moved to breakeven on {position.symbol}"
        else:  # trail
            trail = position.mark * (_d("0.99") if position.side == "long" else _d("1.01"))
            position.stop_loss = trail
            position.health = "trailing"
            msg = f"Trailing stop updated on {position.symbol}"
            await self._add_activity(
                account.id,
                title="Trailing Stop Updated",
                detail=msg,
                category="trailing_stop",
                severity="info",
            )

        if action != "trail":
            await self._add_activity(
                account.id,
                title="Position Action",
                detail=msg,
                category="system",
                severity="info",
            )
        await self.session.commit()
        loaded = await self.repo.get_account(user_id)
        assert loaded is not None
        pos_out = None if position.status == "closed" else self._position_out(position)
        return PlaceLiveOrderOut(message=msg, position=pos_out, desk=self._to_desk(loaded))

    async def emergency(self, user_id: UUID, payload: EmergencyStopRequest) -> EmergencyStopOut:
        account = await self.ensure_account(user_id)
        action = payload.action
        result: dict = {}

        if action == "close_all":
            positions = await self.repo.list_open_positions(account.id)
            for p in positions:
                p.status = "closed"
                p.closed_at = datetime.now(timezone.utc)
                p.health = "closing"
            result["closed"] = len(positions)
            detail = f"Closed {len(positions)} position(s)."
        elif action == "cancel_all":
            orders = await self.repo.list_open_orders(account.id)
            for o in orders:
                o.status = "cancelled"
            result["cancelled"] = len(orders)
            detail = f"Cancelled {len(orders)} order(s)."
        elif action == "disable_auto":
            account.auto_trading = False
            detail = "Auto trading disabled."
        elif action == "lock":
            account.trading_locked = True
            account.auto_trading = False
            detail = "Trading locked."
        else:
            account.risk_only_mode = True
            detail = "Risk-only mode enabled."

        await self.repo.add(
            LiveEmergencyEvent(
                id=uuid4(),
                user_id=user_id,
                account_id=account.id,
                action=action,
                detail=detail,
                result=result,
            )
        )
        await self._add_activity(
            account.id,
            title="Emergency Stop",
            detail=detail,
            category="risk_alert",
            severity="critical",
        )
        await self.session.commit()
        loaded = await self.repo.get_account(user_id)
        assert loaded is not None
        return EmergencyStopOut(message=detail, action=action, result=result, desk=self._to_desk(loaded))

    async def ask_ai(self, user_id: UUID, payload: AskAiRequest) -> AskAiOut:
        await self.ensure_account(user_id)
        reply = AI_REPLIES.get(payload.prompt_id)
        if reply is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown prompt_id")
        return AskAiOut(prompt_id=payload.prompt_id, reply=reply)
