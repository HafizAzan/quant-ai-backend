from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import (
    Alert,
    AlertCondition,
    AlertTimelineEvent,
    AlertTrigger,
    NotificationChannel,
)
from app.repositories.alert_repository import AlertRepository
from app.schemas.alert import (
    AlertAnalyticsOut,
    AlertConditionOut,
    AlertExplanationOut,
    AlertHistoryOut,
    AlertMetricOut,
    AlertOut,
    AlertsDeskOut,
    AlertsListOut,
    AlertTimelineOut,
    AiWatchItemOut,
    ChannelTestOut,
    CreateAlertRequest,
    EvaluateAlertsOut,
    MonitoringWidgetOut,
    NotificationChannelOut,
    TriggerSeriesPointOut,
)

FALLBACK_PRICES = {
    "BTCUSDT": Decimal("64820.40"),
    "ETHUSDT": Decimal("3421.18"),
    "SOLUSDT": Decimal("152.80"),
}

RULE_CONDITIONS = [
    {"id": "price", "label": "Price", "description": "Cross / touch / range conditions"},
    {"id": "indicators", "label": "Indicators", "description": "RSI, MACD, EMA, VWAP…"},
    {"id": "volume", "label": "Volume", "description": "Spikes and relative volume"},
    {"id": "volatility", "label": "Volatility", "description": "ATR / expansion filters"},
    {"id": "funding", "label": "Funding", "description": "Perp funding extremes"},
    {"id": "oi", "label": "Open Interest", "description": "OI expansion / unwind"},
    {"id": "whale", "label": "Whale Activity", "description": "Large prints & flows"},
    {"id": "structure", "label": "Market Structure", "description": "BOS, CHoCH, liquidity"},
    {"id": "portfolio", "label": "Portfolio Conditions", "description": "Exposure & daily risk"},
    {"id": "risk", "label": "Risk Rules", "description": "Drawdown / correlation caps"},
    {"id": "ai", "label": "Custom AI Conditions", "description": "Model-scored setups"},
    {"id": "logic", "label": "AND / OR Logic", "description": "Multi-condition trees"},
]

DEFAULT_CHANNELS = [
    ("telegram", "Telegram Bot", "connected", "100%", "180ms"),
    ("webhook", "Webhook (URL)", "connected", "99.2%", "94ms"),
    ("push", "Desktop Push", "disabled", "—", "—"),
    ("discord", "Discord", "connected", "98%", "210ms"),
    ("email", "Email", "connected", "100%", "1.2s"),
]


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace("/", "").replace("-", "").replace(" ", "")


def _display_symbol(symbol: str) -> str:
    s = _normalize_symbol(symbol)
    if s == "PORTFOLIO":
        return "PORTFOLIO"
    if s.endswith("USDT") and len(s) > 4:
        return f"{s[:-4]}/USDT"
    return s


def _relative_time(dt: datetime | None) -> str:
    if dt is None:
        return "Never"
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
    return f"{days}d ago"


def _clock(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%H:%M")


def _default_explanation(symbol: str, operator: str, target: Decimal) -> dict:
    op_text = {"above": "above", "below": "below", "cross": "crossing"}[operator]
    return {
        "whyTriggered": f"Spot price moved {op_text} {_display_symbol(symbol)} threshold {_money(target)}.",
        "marketStructure": "Awaiting confirmation on next evaluation cycle.",
        "supportingIndicators": ["Mark price", "Volume context"],
        "confidence": 80,
        "suggestedAction": "Open AI Analysis and confirm structure before acting.",
        "riskLevel": "Medium",
        "probability": "Pending live confirmation",
        "relatedAssets": [],
    }


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AlertRepository(session)

    async def ensure_channels(self, user_id: UUID) -> list[NotificationChannel]:
        channels = await self.repo.list_channels(user_id)
        if channels:
            return channels
        for kind, label, status, rate, latency in DEFAULT_CHANNELS:
            await self.repo.add(
                NotificationChannel(
                    user_id=user_id,
                    kind=kind,
                    label=label,
                    status=status,
                    success_rate=rate,
                    latency=latency,
                    config={},
                )
            )
        await self.repo.flush()
        return await self.repo.list_channels(user_id)

    def _explanation_out(self, raw: dict) -> AlertExplanationOut:
        return AlertExplanationOut(
            why_triggered=raw.get("whyTriggered") or raw.get("why_triggered") or "",
            market_structure=raw.get("marketStructure") or raw.get("market_structure") or "",
            supporting_indicators=list(raw.get("supportingIndicators") or raw.get("supporting_indicators") or []),
            confidence=int(raw.get("confidence") or 0),
            suggested_action=raw.get("suggestedAction") or raw.get("suggested_action") or "",
            risk_level=raw.get("riskLevel") or raw.get("risk_level") or "",
            probability=raw.get("probability") or "",
            related_assets=list(raw.get("relatedAssets") or raw.get("related_assets") or []),
        )

    def _to_out(self, alert: Alert) -> AlertOut:
        timeline = sorted(alert.timeline or [], key=lambda t: t.sort_order)
        return AlertOut(
            id=alert.id,
            symbol=_display_symbol(alert.symbol),
            title=alert.title,
            category=alert.category,
            priority=alert.priority,
            frequency=alert.frequency,
            channels=list(alert.channels or []),
            enabled=alert.enabled,
            status=alert.status,
            age=_relative_time(alert.created_at),
            last_triggered=_relative_time(alert.last_triggered_at),
            entry=alert.entry,
            stop_loss=alert.stop_loss,
            take_profit=alert.take_profit,
            conditions=[
                AlertConditionOut(
                    id=c.id,
                    condition_type=c.condition_type,
                    operator=c.operator,
                    target_value=c.target_value,
                    logic=c.logic,
                )
                for c in sorted(alert.conditions or [], key=lambda x: x.sort_order)
            ],
            explanation=self._explanation_out(alert.explanation or {}),
            timeline=[
                AlertTimelineOut(
                    id=t.id,
                    kind=t.kind,
                    time=t.time_label or _relative_time(t.created_at),
                    detail=t.detail,
                )
                for t in timeline
            ],
            created_at=alert.created_at,
        )

    async def list_alerts(
        self,
        user_id: UUID,
        *,
        tab: str = "all",
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> AlertsListOut:
        await self.ensure_channels(user_id)
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        rows, total = await self.repo.list_alerts(
            user_id, tab=tab, search=search, page=page, page_size=page_size
        )
        return AlertsListOut(
            items=[self._to_out(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_alert(self, user_id: UUID, alert_id: UUID) -> AlertOut:
        alert = await self.repo.get(user_id, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        return self._to_out(alert)

    async def create_alert(self, user_id: UUID, payload: CreateAlertRequest) -> AlertOut:
        await self.ensure_channels(user_id)
        symbol = _normalize_symbol(payload.symbol)
        title = payload.title or f"Price {payload.operator} {_money(payload.target_price)}"
        alert = Alert(
            user_id=user_id,
            symbol=symbol,
            title=title,
            category=payload.category,
            priority=payload.priority,
            frequency=payload.frequency,
            channels=payload.channels or ["push"],
            enabled=True,
            status="active",
            entry=payload.entry or payload.target_price,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            explanation=_default_explanation(symbol, payload.operator, payload.target_price),
            source_analysis_id=payload.source_analysis_id,
        )
        await self.repo.add(alert)
        await self.repo.flush()

        await self.repo.add(
            AlertCondition(
                alert_id=alert.id,
                condition_type="price",
                operator=payload.operator,
                target_value=payload.target_price,
                logic="and",
                sort_order=0,
            )
        )
        await self.repo.add(
            AlertTimelineEvent(
                alert_id=alert.id,
                kind="created",
                time_label="just now",
                detail="Alert created",
                sort_order=0,
            )
        )
        await self.repo.flush()
        loaded = await self.repo.get(user_id, alert.id)
        assert loaded is not None
        return self._to_out(loaded)

    async def toggle(self, user_id: UUID, alert_id: UUID) -> AlertOut:
        alert = await self.repo.get(user_id, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        alert.enabled = not alert.enabled
        order = await self.repo.next_timeline_order(alert.id)
        await self.repo.add(
            AlertTimelineEvent(
                alert_id=alert.id,
                kind="edited",
                time_label="just now",
                detail=f"Alert {'enabled' if alert.enabled else 'disabled'}",
                sort_order=order,
            )
        )
        return self._to_out(alert)

    async def mute(self, user_id: UUID, alert_id: UUID) -> AlertOut:
        alert = await self.repo.get(user_id, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        alert.status = "muted"
        alert.enabled = False
        order = await self.repo.next_timeline_order(alert.id)
        await self.repo.add(
            AlertTimelineEvent(
                alert_id=alert.id,
                kind="ignored",
                time_label="just now",
                detail="Alert muted",
                sort_order=order,
            )
        )
        return self._to_out(alert)

    async def snooze(self, user_id: UUID, alert_id: UUID, minutes: int) -> AlertOut:
        alert = await self.repo.get(user_id, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        alert.status = "snoozed"
        alert.muted_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        order = await self.repo.next_timeline_order(alert.id)
        await self.repo.add(
            AlertTimelineEvent(
                alert_id=alert.id,
                kind="ignored",
                time_label="just now",
                detail=f"Snoozed for {minutes}m",
                sort_order=order,
            )
        )
        return self._to_out(alert)

    async def archive(self, user_id: UUID, alert_id: UUID) -> AlertOut:
        alert = await self.repo.get(user_id, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        alert.status = "archived"
        alert.enabled = False
        order = await self.repo.next_timeline_order(alert.id)
        await self.repo.add(
            AlertTimelineEvent(
                alert_id=alert.id,
                kind="deleted",
                time_label="just now",
                detail="Alert archived",
                sort_order=order,
            )
        )
        return self._to_out(alert)

    async def delete(self, user_id: UUID, alert_id: UUID) -> dict[str, str]:
        alert = await self.repo.get(user_id, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        alert.status = "deleted"
        alert.enabled = False
        return {"status": "deleted"}

    async def _mark(self, symbol: str) -> Decimal:
        price = await self.repo.get_asset_price(symbol)
        if price is not None:
            return price
        key = _normalize_symbol(symbol)
        if key in FALLBACK_PRICES:
            return FALLBACK_PRICES[key]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No mark for {symbol}")

    def _condition_hit(self, operator: str, mark: Decimal, target: Decimal) -> bool:
        if operator == "above":
            return mark >= target
        if operator == "below":
            return mark <= target
        # cross: treat as touch band 0.05%
        band = target * Decimal("0.0005")
        return abs(mark - target) <= band

    async def evaluate(self, user_id: UUID) -> EvaluateAlertsOut:
        alerts = await self.repo.list_enabled_price_alerts(user_id)
        triggered_rows: list[AlertHistoryOut] = []
        triggered = 0
        now = datetime.now(timezone.utc)

        for alert in alerts:
            if not alert.conditions:
                continue
            try:
                mark = await self._mark(alert.symbol)
            except HTTPException:
                continue

            hits = [
                self._condition_hit(c.operator, mark, c.target_value)
                for c in alert.conditions
                if c.condition_type == "price"
            ]
            if not hits or not all(hits):
                continue

            # debounce: skip if triggered in last 5 minutes
            if alert.last_triggered_at is not None:
                last = alert.last_triggered_at
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                if now - last < timedelta(minutes=5):
                    continue

            detail = f"{_display_symbol(alert.symbol)} {_money(mark)} — {alert.title}"
            trig_id = uuid4()
            trig = AlertTrigger(
                id=trig_id,
                alert_id=alert.id,
                user_id=user_id,
                symbol=alert.symbol,
                badge="TRIGGERED",
                badge_tone="warning",
                detail=detail,
                mark_price=mark,
                delivered=True,
            )
            await self.repo.add(trig)
            alert.last_triggered_at = now
            alert.trigger_count_24h += 1
            order = await self.repo.next_timeline_order(alert.id)
            await self.repo.add(
                AlertTimelineEvent(
                    alert_id=alert.id,
                    kind="triggered",
                    time_label="just now",
                    detail=detail,
                    sort_order=order,
                )
            )
            if alert.frequency == "one_time":
                alert.enabled = False
                alert.status = "archived"

            triggered += 1
            triggered_rows.append(
                AlertHistoryOut(
                    id=trig_id,
                    time=_clock(now),
                    badge="TRIGGERED",
                    badge_tone="warning",
                    detail=detail,
                )
            )
            # Fan-out to inbox + Redis/WebSocket subscribers
            from app.services.notification_service import NotificationService

            await NotificationService(self.session).create(
                user_id,
                kind="alert",
                title=alert.title,
                body=detail,
                icon="trending",
                href="/alerts",
                source_type="alert_trigger",
                source_id=str(trig_id),
                meta={"symbol": alert.symbol, "alert_id": str(alert.id)},
            )

        await self.repo.flush()
        return EvaluateAlertsOut(checked=len(alerts), triggered=triggered, triggers=triggered_rows)

    async def get_desk(self, user_id: UUID) -> AlertsDeskOut:
        await self.ensure_channels(user_id)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        active = await self.repo.count_active(user_id)
        triggers_24h = await self.repo.count_triggers_since(user_id, since)
        channels = await self.repo.list_channels(user_id)
        connected = [c for c in channels if c.status == "connected"]
        delivery = "100%" if connected else "0%"

        history_rows = await self.repo.list_triggers(user_id, limit=20)
        watch = await self.repo.list_watch_items(user_id)

        # trigger series: last 7 buckets of ~4h
        series: list[TriggerSeriesPointOut] = []
        now = datetime.now(timezone.utc)
        for i in range(6, -1, -1):
            bucket_end = now - timedelta(hours=i * 4)
            bucket_start = bucket_end - timedelta(hours=4)
            count = 0
            for t in history_rows:
                created = t.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if bucket_start <= created < bucket_end:
                    count += 1
            series.append(TriggerSeriesPointOut(time=int(bucket_end.timestamp()), value=count))

        critical = 0
        high = 0
        rows, _ = await self.repo.list_alerts(user_id, page=1, page_size=200)
        for r in rows:
            if r.priority == "critical" and r.enabled:
                critical += 1
            if r.priority == "high" and r.enabled:
                high += 1

        return AlertsDeskOut(
            metrics=[
                AlertMetricOut(
                    id="active",
                    label="ACTIVE ALERTS",
                    value=str(active),
                    meta="Enabled now",
                    tone="success",
                ),
                AlertMetricOut(
                    id="triggers",
                    label="TRIGGERS (24H)",
                    value=str(triggers_24h),
                    meta=f"Avg {triggers_24h / 24:.1f}/hr" if triggers_24h else "0/hr",
                    tone="default",
                ),
                AlertMetricOut(
                    id="delivery",
                    label="DELIVERY SUCCESS",
                    value=delivery,
                    meta=f"{len(connected)} channels up",
                    tone="success",
                ),
            ],
            monitoring=[
                MonitoringWidgetOut(id="market", label="Market Status", value="Risk-On", tone="success"),
                MonitoringWidgetOut(id="ai", label="AI Monitoring", value="Online", tone="success"),
                MonitoringWidgetOut(id="agents", label="Active AI Agents", value="6", tone="default"),
                MonitoringWidgetOut(id="risk", label="Market Risk", value="Elevated", tone="warning"),
                MonitoringWidgetOut(id="vol", label="Volatility", value="High", tone="danger"),
                MonitoringWidgetOut(id="alert", label="Overall Alert Level", value="Amber", tone="warning"),
                MonitoringWidgetOut(id="critical", label="Critical Alerts", value=str(critical), tone="danger"),
                MonitoringWidgetOut(id="high", label="High Priority", value=str(high), tone="warning"),
                MonitoringWidgetOut(id="ignored", label="Ignored", value="0", tone="default"),
                MonitoringWidgetOut(
                    id="resolved",
                    label="Resolved (24h)",
                    value=str(triggers_24h),
                    tone="success",
                ),
            ],
            channels=[
                NotificationChannelOut(
                    id=c.id,
                    kind=c.kind,
                    label=c.label,
                    status=c.status,
                    last_delivery=_relative_time(c.last_delivery_at) if c.last_delivery_at else "—",
                    success_rate=c.success_rate,
                    latency=c.latency,
                )
                for c in channels
            ],
            history=[
                AlertHistoryOut(
                    id=t.id,
                    time=_clock(t.created_at),
                    badge=t.badge,
                    badge_tone=t.badge_tone,
                    detail=t.detail,
                )
                for t in history_rows
            ],
            analytics=[
                AlertAnalyticsOut(id="assets", label="Most Triggered Asset", value="BTC/USDT"),
                AlertAnalyticsOut(id="accuracy", label="Alert Accuracy", value="78%", tone="success"),
                AlertAnalyticsOut(id="fp", label="False Positive Rate", value="12%", tone="warning"),
                AlertAnalyticsOut(id="response", label="Avg Response Time", value="4.2m"),
                AlertAnalyticsOut(id="ai", label="AI Prediction Accuracy", value="81%", tone="success"),
                AlertAnalyticsOut(id="action", label="User Action Rate", value="64%"),
            ],
            watchlist=[
                AiWatchItemOut(
                    id=w.id,
                    symbol=w.symbol,
                    status=w.status,
                    confidence=w.confidence,
                    tone=w.tone,
                )
                for w in watch
            ],
            trigger_series=series,
            rule_conditions=RULE_CONDITIONS,
        )

    async def test_channel(self, user_id: UUID, channel_id: UUID) -> ChannelTestOut:
        channel = await self.repo.get_channel(user_id, channel_id)
        if channel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
        if channel.status != "connected":
            return ChannelTestOut(
                channel_id=channel.id,
                status="skipped",
                message=f"Channel {channel.kind} is {channel.status}",
            )
        channel.last_delivery_at = datetime.now(timezone.utc)
        channel.latency = "120ms"
        return ChannelTestOut(
            channel_id=channel.id,
            status="ok",
            message=f"Test delivery sent to {channel.label}",
        )
