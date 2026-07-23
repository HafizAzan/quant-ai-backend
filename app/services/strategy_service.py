from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import re
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy import BacktestRun, Strategy, StrategyEdge, StrategyNode
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.strategy import (
    AiAssistOut,
    AiAssistRequest,
    BacktestMetricsOut,
    BacktestRunOut,
    CreateStrategyRequest,
    GenerateStrategyOut,
    GenerateStrategyRequest,
    RunBacktestRequest,
    SaveCanvasRequest,
    StrategiesWorkspaceOut,
    StrategyCanvasOut,
    StrategyDetailOut,
    StrategyEdgeOut,
    StrategyListOut,
    StrategyNodeOut,
    StrategyOut,
    StrategyValidationIssueOut,
    UpdateStrategyRequest,
)

FILTER_OPTIONS = {
    "markets": [
        {"value": "all", "label": "All markets"},
        {"value": "BTC/USDT", "label": "BTC/USDT"},
        {"value": "ETH/USDT", "label": "ETH/USDT"},
        {"value": "SOL/USDT", "label": "SOL/USDT"},
    ],
    "exchanges": [
        {"value": "all", "label": "All exchanges"},
        {"value": "Binance", "label": "Binance"},
    ],
    "types": [
        {"value": "all", "label": "All types"},
        {"value": "Momentum", "label": "Momentum"},
        {"value": "Mean Reversion", "label": "Mean Reversion"},
        {"value": "Breakout", "label": "Breakout"},
    ],
    "statuses": [
        {"value": "all", "label": "All statuses"},
        {"value": "active", "label": "Active"},
        {"value": "paused", "label": "Paused"},
        {"value": "draft", "label": "Draft"},
    ],
    "risks": [
        {"value": "all", "label": "All risk"},
        {"value": "low", "label": "Low"},
        {"value": "medium", "label": "Medium"},
        {"value": "high", "label": "High"},
    ],
}

AI_ASSISTANT_ACTIONS = [
    {"id": "generate", "label": "Generate Strategy", "description": "Create a workflow from a natural-language brief"},
    {"id": "optimize", "label": "Optimize Strategy", "description": "Tune parameters for risk-adjusted return"},
    {"id": "explain", "label": "Explain Strategy", "description": "Plain-English walkthrough of the graph"},
    {"id": "weaknesses", "label": "Find Weaknesses", "description": "Surface fragile edges and missing guards"},
    {"id": "risk", "label": "Improve Risk", "description": "Suggest stops, sizing, and filters"},
    {"id": "indicators", "label": "Suggest Indicators", "description": "Recommend complementary signals"},
    {"id": "convert", "label": "English → Strategy", "description": "Compile intent into nodes and edges"},
]

GENERATE_PIPELINE = [
    {"id": "prompt", "label": "User Prompt"},
    {"id": "agent", "label": "AI Strategy Agent"},
    {"id": "nodes", "label": "Visual Nodes Generate"},
    {"id": "validate", "label": "Validate Strategy"},
    {"id": "backtest", "label": "Backtest"},
    {"id": "paper", "label": "Paper Trade"},
]

PROMPT_EXAMPLES = [
    "Create a BTC scalping strategy using EMA 20, EMA 50, RSI, and 1% risk.",
    "Build an ETH mean-reversion bot with Bollinger Bands and tight stops.",
    "Design a SOL breakout strategy with ATR trailing stop and session filter.",
]


def _d(v: float | int | str) -> Decimal:
    return Decimal(str(v))


def _date_label(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%b %d, %Y")


def _validate_canvas(strategy: Strategy, nodes: list[StrategyNode], edges: list[StrategyEdge]) -> list[StrategyValidationIssueOut]:
    issues: list[StrategyValidationIssueOut] = []
    if not nodes:
        return [StrategyValidationIssueOut(code="missing_trigger", label="Missing Trigger", tone="danger")]

    has_trigger = any(n.category == "trigger" for n in nodes)
    has_risk = any(n.category == "risk" for n in nodes)
    has_action = any(n.category == "action" for n in nodes)
    node_keys = {n.node_key for n in nodes}

    if not has_trigger:
        issues.append(StrategyValidationIssueOut(code="missing_trigger", label="Missing Trigger", tone="danger"))
    if not has_risk:
        issues.append(StrategyValidationIssueOut(code="missing_risk", label="Missing Risk Rule", tone="warning"))
    if any(e.source_key not in node_keys or e.target_key not in node_keys for e in edges):
        issues.append(StrategyValidationIssueOut(code="invalid_connection", label="Invalid Connection", tone="danger"))
    if not strategy.last_backtest_label:
        issues.append(StrategyValidationIssueOut(code="backtest_required", label="Backtest Required", tone="warning"))

    invalid = any(i.code == "invalid_connection" for i in issues)
    if has_trigger and has_action and strategy.status == "active" and not invalid:
        issues.append(StrategyValidationIssueOut(code="live_ready", label="Live Ready", tone="success"))
    elif has_trigger and has_action and not invalid:
        issues.append(StrategyValidationIssueOut(code="ready", label="Ready", tone="info"))
    return issues


def _detect_symbol(prompt: str) -> str:
    upper = prompt.upper()
    if "ETH" in upper:
        return "ETH/USDT"
    if "SOL" in upper:
        return "SOL/USDT"
    return "BTC/USDT"


def _detect_timeframe(prompt: str) -> str:
    match = re.search(r"\b(1m|5m|15m|1h|4h|1d)\b", prompt, re.I)
    if match:
        return match.group(1).lower()
    if re.search(r"scalp", prompt, re.I):
        return "5m"
    if re.search(r"swing", prompt, re.I):
        return "4h"
    return "15m"


def _detect_risk_pct(prompt: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*risk", prompt, re.I)
    return float(match.group(1)) if match else 1.0


def _detect_type(prompt: str) -> str:
    if re.search(r"mean.?reversion", prompt, re.I):
        return "Mean Reversion"
    if re.search(r"breakout", prompt, re.I):
        return "Breakout"
    return "Momentum"


def _mock_backtest_metrics(strategy: Strategy, range_label: str) -> dict:
    seed = int(hashlib.md5(f"{strategy.id}:{strategy.version}:{range_label}".encode()).hexdigest()[:8], 16)
    win = 48 + (seed % 30) + (strategy.ai_confidence / 20)
    pf = 1.1 + ((seed // 7) % 25) / 10
    dd = 6 + ((seed // 3) % 16)
    sharpe = 0.8 + ((seed // 11) % 20) / 10
    trades = 40 + (seed % 200)
    monthly = round(2 + ((seed // 5) % 90) / 10, 1)
    return {
        "win_rate": round(min(win, 82), 1),
        "profit_factor": round(min(pf, 3.5), 2),
        "drawdown": round(dd, 1),
        "sharpe": round(sharpe, 2),
        "trades": trades,
        "monthly_return": f"+{monthly}%",
    }


def _default_canvas_nodes(symbol: str, timeframe: str, risk_pct: float = 1.0) -> list[dict]:
    return [
        {
            "node_key": "trigger",
            "category": "trigger",
            "type_id": "market_open",
            "title": "TRIGGER: CANDLE CLOSE",
            "description": f"Asset: {symbol} · {timeframe}",
            "validation": "valid",
            "ports": [{"id": "out", "side": "out"}],
            "config": {"symbol": symbol, "timeframe": timeframe},
            "sort_order": 0,
        },
        {
            "node_key": "condition",
            "category": "condition",
            "type_id": "condition_group",
            "title": "CONDITION GROUP (AND)",
            "lines": ["IF EMA (20) crosses above EMA (50)", "AND RSI (14) between 45–65"],
            "validation": "valid",
            "ports": [
                {"id": "in", "side": "in"},
                {"id": "out-true", "side": "out", "label": "true"},
                {"id": "out-false", "side": "out", "label": "false"},
            ],
            "config": {"emaFast": 20, "emaSlow": 50, "rsi": 14},
            "sort_order": 1,
        },
        {
            "node_key": "risk",
            "category": "risk",
            "type_id": "risk_position_size",
            "title": "RISK: POSITION SIZE",
            "description": f"Cap risk at {risk_pct}% of portfolio equity per trade.",
            "validation": "valid",
            "ports": [{"id": "in", "side": "in"}, {"id": "out", "side": "out"}],
            "config": {"riskPercent": risk_pct},
            "sort_order": 2,
        },
        {
            "node_key": "buy",
            "category": "action",
            "type_id": "action_buy",
            "title": "ACTION: BUY",
            "description": f"Enter long on {symbol} with sized risk.",
            "validation": "valid",
            "ports": [{"id": "in", "side": "in"}],
            "sort_order": 3,
        },
        {
            "node_key": "wait",
            "category": "action",
            "type_id": "action_wait",
            "title": "ACTION: WAIT",
            "description": "Hold flat until next valid crossover.",
            "validation": "idle",
            "ports": [{"id": "in", "side": "in"}],
            "sort_order": 4,
        },
    ]


DEFAULT_EDGES = [
    {"edge_key": "e1", "source_key": "trigger", "target_key": "condition"},
    {"edge_key": "e2", "source_key": "condition", "target_key": "risk", "label": "true"},
    {"edge_key": "e3", "source_key": "condition", "target_key": "wait", "label": "false"},
    {"edge_key": "e4", "source_key": "risk", "target_key": "buy"},
]


class StrategyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = StrategyRepository(session)

    def get_workspace(self) -> StrategiesWorkspaceOut:
        return StrategiesWorkspaceOut(
            page_meta={
                "title": "Strategies",
                "subtitle": "Manage institutional-grade algorithms and build complex logic via AI-assisted canvas.",
            },
            filter_options=FILTER_OPTIONS,
            ai_assistant_actions=AI_ASSISTANT_ACTIONS,
            builder_toolbar=[
                {"id": "import", "label": "Import"},
                {"id": "branch", "label": "Branch"},
                {"id": "chart", "label": "Chart"},
                {"id": "ai", "label": "AI"},
                {"id": "add", "label": "Add node"},
            ],
            card_actions=[
                {"id": "open", "label": "Open"},
                {"id": "edit", "label": "Edit"},
                {"id": "duplicate", "label": "Duplicate"},
                {"id": "export", "label": "Export"},
                {"id": "backtest", "label": "Backtest"},
                {"id": "paper", "label": "Paper Trade"},
                {"id": "deploy", "label": "Deploy"},
                {"id": "archive", "label": "Archive"},
            ],
            generate_pipeline_steps=GENERATE_PIPELINE,
            generate_prompt_examples=PROMPT_EXAMPLES,
            backtest_defaults=BacktestMetricsOut(
                win_rate=_d("68.4"),
                profit_factor=_d("2.14"),
                drawdown=_d("12.5"),
                sharpe=_d("1.42"),
                trades=186,
                monthly_return="+6.2%",
            ),
        )

    def _to_strategy_out(self, s: Strategy) -> StrategyOut:
        return StrategyOut(
            id=s.id,
            name=s.name,
            symbol=s.symbol,
            timeframe=s.timeframe,
            status=s.status,
            win_rate=s.win_rate,
            profit_factor=s.profit_factor,
            drawdown=s.drawdown,
            last_backtest=s.last_backtest_label or "",
            description=s.description,
            markets=list(s.markets or []),
            timeframes=list(s.timeframes or []),
            version=s.version,
            created_at=s.created_at,
            updated_at=s.updated_at,
            created_at_label=_date_label(s.created_at),
            updated_at_label=_date_label(s.updated_at),
            ai_confidence=s.ai_confidence,
            estimated_risk=s.estimated_risk,
            estimated_monthly_return=s.estimated_monthly_return,
            max_drawdown=s.max_drawdown,
            exchange=s.exchange,
            strategy_type=s.strategy_type,
            tags=list(s.tags or []),
            author=s.author,
        )

    def _to_canvas(self, s: Strategy) -> StrategyCanvasOut:
        nodes = sorted(s.nodes or [], key=lambda n: n.sort_order)
        return StrategyCanvasOut(
            strategy_id=s.id,
            nodes=[
                StrategyNodeOut(
                    id=n.node_key,
                    category=n.category,
                    type_id=n.type_id,
                    title=n.title,
                    description=n.description,
                    lines=list(n.lines) if n.lines else None,
                    collapsed=n.collapsed,
                    validation=n.validation,
                    config=n.config,
                    ports=list(n.ports) if n.ports else None,
                )
                for n in nodes
            ],
            edges=[
                StrategyEdgeOut(
                    id=e.edge_key,
                    source=e.source_key,
                    target=e.target_key,
                    source_port=e.source_port,
                    target_port=e.target_port,
                    label=e.label,
                    highlighted=e.highlighted,
                    errored=e.errored,
                )
                for e in (s.edges or [])
            ],
        )

    def _to_backtest_out(self, run: BacktestRun) -> BacktestRunOut:
        return BacktestRunOut(
            id=run.id,
            strategy_id=run.strategy_id,
            status=run.status,
            symbol=run.symbol,
            timeframe=run.timeframe,
            range_label=run.range_label,
            win_rate=run.win_rate,
            profit_factor=run.profit_factor,
            drawdown=run.drawdown,
            sharpe=run.sharpe,
            trades=run.trades,
            monthly_return=run.monthly_return,
            metrics=dict(run.metrics or {}),
            error_message=run.error_message,
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
        )

    def _to_detail(self, s: Strategy) -> StrategyDetailOut:
        base = self._to_strategy_out(s)
        latest = None
        if s.backtests:
            latest_run = sorted(s.backtests, key=lambda b: b.created_at, reverse=True)[0]
            latest = self._to_backtest_out(latest_run)
        return StrategyDetailOut(
            **base.model_dump(),
            canvas=self._to_canvas(s),
            validation=_validate_canvas(s, list(s.nodes or []), list(s.edges or [])),
            latest_backtest=latest,
        )

    async def _attach_canvas(self, strategy_id: UUID, nodes: list[dict], edges: list[dict]) -> None:
        for i, n in enumerate(nodes):
            await self.repo.add(
                StrategyNode(
                    id=uuid4(),
                    strategy_id=strategy_id,
                    node_key=n["node_key"],
                    category=n["category"],
                    type_id=n["type_id"],
                    title=n["title"],
                    description=n.get("description"),
                    lines=n.get("lines"),
                    collapsed=bool(n.get("collapsed", False)),
                    validation=n.get("validation", "idle"),
                    config=n.get("config"),
                    ports=n.get("ports"),
                    sort_order=n.get("sort_order", i),
                )
            )
        for e in edges:
            await self.repo.add(
                StrategyEdge(
                    id=uuid4(),
                    strategy_id=strategy_id,
                    edge_key=e["edge_key"],
                    source_key=e["source_key"],
                    target_key=e["target_key"],
                    source_port=e.get("source_port"),
                    target_port=e.get("target_port"),
                    label=e.get("label"),
                    highlighted=bool(e.get("highlighted", False)),
                    errored=bool(e.get("errored", False)),
                )
            )

    async def list_strategies(
        self,
        user_id: UUID,
        *,
        query: str | None = None,
        market: str | None = None,
        exchange: str | None = None,
        strategy_type: str | None = None,
        status: str | None = None,
        risk: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> StrategyListOut:
        items, total = await self.repo.list_strategies(
            user_id,
            query=query,
            market=market,
            exchange=exchange,
            strategy_type=strategy_type,
            status=status,
            risk=risk,
            page=page,
            page_size=page_size,
        )
        return StrategyListOut(
            items=[self._to_strategy_out(s) for s in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_strategy(self, user_id: UUID, strategy_id: UUID) -> StrategyDetailOut:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        return self._to_detail(s)

    async def create_strategy(self, user_id: UUID, payload: CreateStrategyRequest) -> StrategyDetailOut:
        strategy = Strategy(
            id=uuid4(),
            user_id=user_id,
            name=payload.name,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            status=payload.status,
            description=payload.description,
            markets=[payload.symbol],
            timeframes=[payload.timeframe],
            version="v0.1.0",
            ai_confidence=0,
            estimated_risk=payload.estimated_risk,
            estimated_monthly_return="—",
            exchange=payload.exchange,
            strategy_type=payload.strategy_type,
            tags=list(payload.tags or ["draft"]),
            author="You",
        )
        await self.repo.add(strategy)
        await self.repo.flush()
        await self._attach_canvas(
            strategy.id,
            _default_canvas_nodes(payload.symbol, payload.timeframe),
            DEFAULT_EDGES,
        )
        await self.session.commit()
        loaded = await self.repo.get(user_id, strategy.id)
        assert loaded is not None
        return self._to_detail(loaded)

    async def update_strategy(
        self, user_id: UUID, strategy_id: UUID, payload: UpdateStrategyRequest
    ) -> StrategyDetailOut:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(s, key, value)
        if "symbol" in data and data["symbol"]:
            s.markets = [data["symbol"], *[m for m in (s.markets or []) if m != data["symbol"]]]
        if "timeframe" in data and data["timeframe"]:
            s.timeframes = [data["timeframe"], *[t for t in (s.timeframes or []) if t != data["timeframe"]]]
        await self.session.commit()
        loaded = await self.repo.get(user_id, strategy_id)
        assert loaded is not None
        return self._to_detail(loaded)

    async def save_canvas(
        self, user_id: UUID, strategy_id: UUID, payload: SaveCanvasRequest
    ) -> StrategyDetailOut:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        await self.repo.clear_canvas(strategy_id)
        await self.repo.flush()
        nodes = [
            {
                "node_key": n.id,
                "category": n.category,
                "type_id": n.type_id,
                "title": n.title,
                "description": n.description,
                "lines": n.lines,
                "collapsed": n.collapsed,
                "validation": n.validation,
                "config": n.config,
                "ports": n.ports,
                "sort_order": i,
            }
            for i, n in enumerate(payload.nodes)
        ]
        edges = [
            {
                "edge_key": e.id,
                "source_key": e.source,
                "target_key": e.target,
                "source_port": e.source_port,
                "target_port": e.target_port,
                "label": e.label,
                "highlighted": e.highlighted,
                "errored": e.errored,
            }
            for e in payload.edges
        ]
        await self._attach_canvas(strategy_id, nodes, edges)
        s.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        loaded = await self.repo.get(user_id, strategy_id)
        assert loaded is not None
        return self._to_detail(loaded)

    async def duplicate(self, user_id: UUID, strategy_id: UUID) -> StrategyDetailOut:
        source = await self.repo.get(user_id, strategy_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        clone = Strategy(
            id=uuid4(),
            user_id=user_id,
            name=f"{source.name} (Copy)",
            symbol=source.symbol,
            timeframe=source.timeframe,
            status="draft",
            description=source.description,
            markets=list(source.markets or []),
            timeframes=list(source.timeframes or []),
            version="v0.1.0",
            ai_confidence=source.ai_confidence,
            estimated_risk=source.estimated_risk,
            estimated_monthly_return="—",
            win_rate=_d(0),
            profit_factor=_d(0),
            drawdown=_d(0),
            max_drawdown=_d(0),
            exchange=source.exchange,
            strategy_type=source.strategy_type,
            tags=list({*(source.tags or []), "copy"}),
            author=source.author,
            last_backtest_label="",
            last_backtest_at=None,
        )
        await self.repo.add(clone)
        await self.repo.flush()
        nodes = [
            {
                "node_key": n.node_key,
                "category": n.category,
                "type_id": n.type_id,
                "title": n.title,
                "description": n.description,
                "lines": n.lines,
                "collapsed": n.collapsed,
                "validation": n.validation,
                "config": n.config,
                "ports": n.ports,
                "sort_order": n.sort_order,
            }
            for n in source.nodes
        ]
        edges = [
            {
                "edge_key": e.edge_key,
                "source_key": e.source_key,
                "target_key": e.target_key,
                "source_port": e.source_port,
                "target_port": e.target_port,
                "label": e.label,
                "highlighted": e.highlighted,
                "errored": e.errored,
            }
            for e in source.edges
        ]
        await self._attach_canvas(clone.id, nodes, edges)
        await self.session.commit()
        loaded = await self.repo.get(user_id, clone.id)
        assert loaded is not None
        return self._to_detail(loaded)

    async def archive(self, user_id: UUID, strategy_id: UUID) -> StrategyOut:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        s.status = "archived"
        await self.session.commit()
        return self._to_strategy_out(s)

    async def deploy(self, user_id: UUID, strategy_id: UUID) -> StrategyDetailOut:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        issues = _validate_canvas(s, list(s.nodes or []), list(s.edges or []))
        blocking = {i.code for i in issues} & {"missing_trigger", "invalid_connection"}
        if blocking:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Strategy is not deployable")
        if not s.last_backtest_label:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backtest required before deploy")
        s.status = "active"
        await self.session.commit()
        loaded = await self.repo.get(user_id, strategy_id)
        assert loaded is not None
        return self._to_detail(loaded)

    async def delete_strategy(self, user_id: UUID, strategy_id: UUID) -> None:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        await self.repo.delete(s)
        await self.session.commit()

    async def run_backtest(
        self, user_id: UUID, strategy_id: UUID, payload: RunBacktestRequest
    ) -> BacktestRunOut:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        now = datetime.now(timezone.utc)
        metrics = _mock_backtest_metrics(s, payload.range_label)
        run = BacktestRun(
            id=uuid4(),
            strategy_id=s.id,
            user_id=user_id,
            status="completed",
            symbol=payload.symbol or s.symbol,
            timeframe=payload.timeframe or s.timeframe,
            range_label=payload.range_label,
            win_rate=_d(metrics["win_rate"]),
            profit_factor=_d(metrics["profit_factor"]),
            drawdown=_d(metrics["drawdown"]),
            sharpe=_d(metrics["sharpe"]),
            trades=int(metrics["trades"]),
            monthly_return=str(metrics["monthly_return"]),
            metrics=metrics,
            started_at=now,
            finished_at=now,
        )
        await self.repo.add(run)
        s.win_rate = run.win_rate
        s.profit_factor = run.profit_factor
        s.drawdown = run.drawdown
        s.max_drawdown = run.drawdown
        s.estimated_monthly_return = run.monthly_return
        s.last_backtest_at = now
        s.last_backtest_label = _date_label(now)
        await self.session.commit()
        await self.session.refresh(run)
        return self._to_backtest_out(run)

    async def list_backtests(self, user_id: UUID, strategy_id: UUID) -> list[BacktestRunOut]:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        runs = await self.repo.list_backtests(strategy_id)
        return [self._to_backtest_out(r) for r in runs]

    async def generate(self, user_id: UUID, payload: GenerateStrategyRequest) -> GenerateStrategyOut:
        prompt = payload.prompt.strip()
        symbol = _detect_symbol(prompt)
        timeframe = _detect_timeframe(prompt)
        risk_pct = _detect_risk_pct(prompt)
        strategy_type = _detect_type(prompt)
        base = symbol.split("/")[0]
        risk = "low" if risk_pct <= 1 else "medium" if risk_pct <= 2 else "high"
        strategy = Strategy(
            id=uuid4(),
            user_id=user_id,
            name=f"AI {base} Scalper",
            symbol=symbol,
            timeframe=timeframe,
            status="draft",
            description=prompt,
            markets=[symbol],
            timeframes=[timeframe],
            version="v0.1.0-ai",
            ai_confidence=78,
            estimated_risk=risk,
            estimated_monthly_return="—",
            exchange="Binance",
            strategy_type=strategy_type,
            tags=["ai-generated", base.lower(), "draft"],
            author="AI Strategy Agent",
        )
        await self.repo.add(strategy)
        await self.repo.flush()
        await self._attach_canvas(
            strategy.id,
            _default_canvas_nodes(symbol, timeframe, risk_pct),
            DEFAULT_EDGES,
        )
        await self.session.commit()
        loaded = await self.repo.get(user_id, strategy.id)
        assert loaded is not None
        return GenerateStrategyOut(strategy=self._to_detail(loaded), pipeline_steps=GENERATE_PIPELINE)

    async def ai_assist(self, user_id: UUID, strategy_id: UUID, payload: AiAssistRequest) -> AiAssistOut:
        s = await self.repo.get(user_id, strategy_id)
        if s is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        action = payload.action
        responses = {
            "optimize": (
                "Optimization suggestions",
                f"{s.name} can tighten entries with RSI band filters and reduce size after 2 consecutive losses.",
                ["Raise EMA separation threshold", "Add max daily loss guard", "Prefer London–NY overlap only"],
            ),
            "explain": (
                "Strategy explanation",
                f"{s.name} triggers on candle close for {s.symbol}, evaluates conditions, sizes risk, then enters or waits.",
                [f"Primary market: {s.symbol}", f"Type: {s.strategy_type}", f"Timeframe: {s.timeframe}"],
            ),
            "weaknesses": (
                "Weaknesses found",
                "Missing session filter and no explicit stop-loss node increase overnight gap risk.",
                ["Add session_filter node", "Attach stop_loss action", "Validate false-branch wait logic"],
            ),
            "risk": (
                "Risk improvements",
                f"Estimated risk is {s.estimated_risk}. Cap per-trade risk and enforce max drawdown halt.",
                ["Risk 0.5–1% per trade", "Halt after -4% daily DD", "Trail winners at 1.5 ATR"],
            ),
            "indicators": (
                "Indicator suggestions",
                "Complement current logic with volume confirmation and ATR expansion.",
                ["Volume > 1.5x SMA", "ATR(14) rising", "VWAP reclaim filter"],
            ),
            "convert": (
                "English → Strategy",
                "Intent compiled into trigger → condition → risk → action graph. Review canvas and run backtest.",
                ["Open canvas", "Run backtest", "Deploy to paper"],
            ),
            "generate": (
                "Generate Strategy",
                "Use POST /strategies/generate with a natural-language prompt to create a draft graph.",
                PROMPT_EXAMPLES[:2],
            ),
        }
        title, detail, suggestions = responses.get(
            action,
            ("AI Assist", "No additional guidance for this action.", []),
        )
        return AiAssistOut(action=action, title=title, detail=detail, suggestions=suggestions)
