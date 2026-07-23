from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatThread, CommandExecution
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import (
    ChatMessageOut,
    ChatThreadDetailOut,
    ChatThreadListOut,
    ChatThreadOut,
    ChatWorkspaceOut,
    CommandExecutionResultOut,
    CommandsListOut,
    CreateThreadRequest,
    PlatformCommandOut,
    ResolveCommandOut,
    SendMessageOut,
    SendMessageRequest,
    UpdateThreadRequest,
)
from app.services.command_resolver import (
    COMMAND_PROMPTS,
    PLATFORM_COMMANDS,
    filter_platform_commands,
    resolve_platform_command,
    to_execution_result,
)

ENGINE = "GPT-4o-Market-Enhanced"
TOKENS_LIMIT = 32000


def _relative_time(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = int((now - dt).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = seconds // 86400
    if days == 1:
        return "Yesterday"
    return f"{days} days ago"


def _command_out(cmd: dict) -> PlatformCommandOut:
    return PlatformCommandOut(
        id=cmd["id"],
        label=cmd["label"],
        description=cmd["description"],
        kind=cmd["kind"],
        module=cmd["module"],
        href=cmd["href"],
        examples=list(cmd.get("examples") or []),
        keywords=list(cmd.get("keywords") or []),
        param_keys=list(cmd.get("param_keys") or []),
        slash=cmd.get("slash"),
    )


def _parse_command_result(raw: dict | None) -> CommandExecutionResultOut | None:
    if not raw:
        return None
    return CommandExecutionResultOut.model_validate(raw)


def _heuristic_reply(text: str, symbol: str | None) -> tuple[str | None, list[dict] | None, list[dict] | None, str, int]:
    """Template AI reply until real LLM orchestration is wired."""
    lower = text.lower()
    sym = symbol or "BTC/USDT"
    bias = "neutral"
    confidence = 70

    if any(k in lower for k in ("bos", "choch", "liquidity", "structure", "wedge", "pattern")):
        bias = "bullish"
        confidence = 84
        sections = [
            {
                "id": "exec",
                "title": "Executive Summary",
                "default_open": True,
                "blocks": [
                    {
                        "type": "text",
                        "text": f"{sym} structure read: higher lows intact with compression near resistance — watch for liquidity sweep before continuation.",
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
                            "Higher lows intact on the active timeframe",
                            "Resistance compression into the apex",
                            "Volume tapering into the pattern",
                        ],
                    },
                    {
                        "type": "callout",
                        "tone": "warning",
                        "text": "Avoid chasing breakouts before a confirmed close beyond structure.",
                    },
                ],
            },
            {
                "id": "setup",
                "title": "Trade Setup",
                "default_open": True,
                "blocks": [
                    {
                        "type": "code",
                        "language": "setup",
                        "code": "Entry: reclaim of structure\nSL: below demand zone\nTP1: prior swing high\nTP2: measured move",
                    }
                ],
            },
        ]
        return None, sections, None, bias, confidence

    if any(k in lower for k in ("top", "perform", "sector", "leader", "rank")):
        bias = "bullish"
        confidence = 78
        sections = [
            {
                "id": "exec",
                "title": "Executive Summary",
                "default_open": True,
                "blocks": [
                    {
                        "type": "text",
                        "text": "Tech-correlated crypto assets are outperforming on the 24h window, led by SOL with strong flow.",
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
                            {"asset": "SOL/USD", "performance": "+12.4%", "performanceValue": 12.4, "spxCorr": "0.42"},
                            {"asset": "LINK/USD", "performance": "+8.7%", "performanceValue": 8.7, "spxCorr": "0.58"},
                            {"asset": "BTC/USD", "performance": "+5.2%", "performanceValue": 5.2, "spxCorr": "0.71"},
                        ],
                    },
                    {
                        "type": "callout",
                        "tone": "info",
                        "text": "SOL is currently leading the sector due to high NFT volume and institutional inflows.",
                    },
                ],
            },
        ]
        return None, sections, None, bias, confidence

    content = (
        "Got it. I can analyze markets, open workspaces, create alerts, or review trades — "
        "try a platform command or type / for the registry."
    )
    blocks = [
        {
            "type": "callout",
            "tone": "info",
            "text": 'Tip: "Open Paper Trading", "Compare BTC vs ETH", or "/alert" unlock full platform control.',
        }
    ]
    return content, None, blocks, bias, confidence


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ChatRepository(session)

    def _to_thread_out(self, thread: ChatThread) -> ChatThreadOut:
        return ChatThreadOut(
            id=thread.id,
            title=thread.title,
            preview=thread.preview,
            symbol=thread.symbol,
            bias=thread.bias,
            confidence=thread.confidence,
            engine=thread.engine,
            tokens_used=thread.tokens_used,
            tokens_limit=thread.tokens_limit,
            timestamp=_relative_time(thread.updated_at),
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    def _to_message_out(self, msg: ChatMessage) -> ChatMessageOut:
        return ChatMessageOut(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            image_label=msg.image_label,
            sections=list(msg.sections) if msg.sections else None,
            blocks=list(msg.blocks) if msg.blocks else None,
            command_result=_parse_command_result(msg.command_result if isinstance(msg.command_result, dict) else None),
            stream_status=msg.stream_status,
            created_at=msg.created_at,
        )

    def get_workspace(self) -> ChatWorkspaceOut:
        return ChatWorkspaceOut(
            engine=ENGINE,
            tokens_used=1482,
            tokens_limit=TOKENS_LIMIT,
            suggested_prompts=[*COMMAND_PROMPTS[:6], "Explain BOS", "Explain CHoCH", "Find Liquidity"],
            empty_state_prompts=list(COMMAND_PROMPTS),
            response_actions=[
                {"id": "analyze-chart", "label": "Analyze Chart"},
                {"id": "open-ai-analysis", "label": "Open in AI Analysis"},
                {"id": "save-analysis", "label": "Save Analysis"},
                {"id": "create-alert", "label": "Create Alert"},
                {"id": "backtest", "label": "Backtest Strategy"},
                {"id": "paper-trade", "label": "Paper Trade"},
            ],
            quick_actions=[
                {"id": "attach-data", "label": "Attach Data"},
                {"id": "live-ticker", "label": "Live Ticker"},
                {"id": "symbol", "label": "Symbol"},
                {"id": "tv-shot", "label": "TV Screenshot"},
            ],
            symbol_options=[
                {"value": "BTCUSDT", "label": "BTC/USDT"},
                {"value": "ETHUSDT", "label": "ETH/USDT"},
                {"value": "SOLUSDT", "label": "SOL/USDT"},
            ],
            market_cap={
                "title": "Global Market Cap",
                "value": "$2.45T",
                "change_percent": 2.1,
                "bars": [42, 55, 48, 62, 58, 70, 66, 78, 72, 85, 80, 92],
            },
            fear_greed={
                "title": "Fear & Greed Index",
                "score": 65,
                "zone": "GREED",
                "description": "Sentiment remains bullish",
            },
            realtime_signals=[
                {
                    "id": "btc-outflow",
                    "tone": "danger",
                    "title": "BTC Large Outflow",
                    "detail": "Binance -> Cold Wallet",
                },
                {
                    "id": "eth-cross",
                    "tone": "success",
                    "title": "Golden Cross ETH",
                    "detail": "MA50 / MA200 4H",
                },
            ],
            pro_analysis={
                "title": "Pro Analysis Active",
                "description": "Enhanced market reasoning enabled for this session.",
            },
            commands=[_command_out(c) for c in PLATFORM_COMMANDS],
        )

    def list_commands(self, query: str | None = None) -> CommandsListOut:
        items = filter_platform_commands(query or "")
        return CommandsListOut(items=[_command_out(c) for c in items], prompts=list(COMMAND_PROMPTS))

    def resolve_command(self, query: str) -> ResolveCommandOut:
        intent = resolve_platform_command(query)
        if intent is None:
            return ResolveCommandOut(
                matched=False,
                result=None,
                suggestions=[_command_out(c) for c in filter_platform_commands(query)[:5]],
            )
        result = to_execution_result(intent)
        return ResolveCommandOut(
            matched=True,
            result=CommandExecutionResultOut.model_validate(result),
            suggestions=[],
        )

    async def list_threads(self, user_id: UUID, *, page: int = 1, page_size: int = 50) -> ChatThreadListOut:
        items, total = await self.repo.list_threads(user_id, page=page, page_size=page_size)
        return ChatThreadListOut(items=[self._to_thread_out(t) for t in items], total=total)

    async def get_thread(self, user_id: UUID, thread_id: UUID) -> ChatThreadDetailOut:
        thread = await self.repo.get_thread(user_id, thread_id)
        if thread is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found")
        base = self._to_thread_out(thread)
        return ChatThreadDetailOut(
            **base.model_dump(),
            messages=[self._to_message_out(m) for m in thread.messages],
        )

    async def create_thread(self, user_id: UUID, payload: CreateThreadRequest) -> ChatThreadDetailOut:
        thread = ChatThread(
            id=uuid4(),
            user_id=user_id,
            title=payload.title or "New Chat",
            preview="",
            symbol=payload.symbol,
            bias="neutral",
            confidence=0,
            engine=ENGINE,
            tokens_used=0,
            tokens_limit=TOKENS_LIMIT,
        )
        await self.repo.add(thread)
        await self.session.commit()
        loaded = await self.repo.get_thread(user_id, thread.id)
        assert loaded is not None
        base = self._to_thread_out(loaded)
        return ChatThreadDetailOut(**base.model_dump(), messages=[])

    async def update_thread(
        self, user_id: UUID, thread_id: UUID, payload: UpdateThreadRequest
    ) -> ChatThreadOut:
        thread = await self.repo.get_thread(user_id, thread_id)
        if thread is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found")
        if payload.title is not None:
            thread.title = payload.title
        await self.session.commit()
        loaded = await self.repo.get_thread(user_id, thread_id)
        assert loaded is not None
        return self._to_thread_out(loaded)

    async def delete_thread(self, user_id: UUID, thread_id: UUID) -> None:
        thread = await self.repo.get_thread(user_id, thread_id)
        if thread is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found")
        await self.repo.delete(thread)
        await self.session.commit()

    async def send_message(self, user_id: UUID, thread_id: UUID, payload: SendMessageRequest) -> SendMessageOut:
        thread = await self.repo.get_thread(user_id, thread_id)
        if thread is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found")

        now = datetime.now(timezone.utc)
        user_msg = ChatMessage(
            id=uuid4(),
            thread_id=thread.id,
            role="user",
            content=payload.content,
            image_label=payload.image_label,
            stream_status="complete",
            created_at=now,
        )
        await self.repo.add(user_msg)
        await self.repo.flush()

        intent = resolve_platform_command(payload.content)
        command_result = None
        sections = None
        blocks = None
        content: str | None
        bias = thread.bias
        confidence = thread.confidence

        if intent is not None:
            command_result = to_execution_result(intent)
            content = (
                "Command recognized. The AI Command Center can route this into the matching platform module."
            )
            if intent.get("params", {}).get("symbol"):
                thread.symbol = str(intent["params"]["symbol"])
        else:
            from app.agents.chat_agent import ChatAgent

            symbol = payload.symbol or thread.symbol
            agent_out = await ChatAgent().reply(payload.content, context={"symbol": symbol})
            if agent_out.get("engine") == "llm":
                content, sections, blocks, bias, confidence = (
                    agent_out["content"],
                    None,
                    None,
                    "neutral",
                    72,
                )
            else:
                content, sections, blocks, bias, confidence = _heuristic_reply(payload.content, symbol)

        assistant = ChatMessage(
            id=uuid4(),
            thread_id=thread.id,
            role="assistant",
            content=content,
            sections=sections,
            blocks=blocks,
            command_result=command_result,
            stream_status="complete",
            created_at=datetime.now(timezone.utc),
        )
        await self.repo.add(assistant)
        await self.repo.flush()

        if intent is not None and command_result is not None:
            await self.repo.add_execution(
                CommandExecution(
                    id=uuid4(),
                    user_id=user_id,
                    thread_id=thread.id,
                    message_id=assistant.id,
                    command_id=intent["command_id"],
                    raw=payload.content,
                    kind=intent["kind"],
                    module=intent["module"],
                    href=intent["href"],
                    confidence=float(intent["confidence"]),
                    params=dict(intent.get("params") or {}),
                    status="ready",
                    summary=command_result["summary"],
                )
            )

        if thread.title in {"", "New Chat"}:
            thread.title = payload.content[:72] + ("..." if len(payload.content) > 72 else "")
        thread.preview = (content or payload.content)[:160]
        thread.bias = bias
        thread.confidence = confidence
        if payload.symbol:
            thread.symbol = payload.symbol
        estimated_tokens = max(12, len(payload.content) // 4 + 40)
        thread.tokens_used = min(thread.tokens_limit, thread.tokens_used + estimated_tokens)
        thread.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(thread)
        await self.session.refresh(user_msg)
        await self.session.refresh(assistant)
        return SendMessageOut(
            thread=self._to_thread_out(thread),
            user_message=self._to_message_out(user_msg),
            assistant_message=self._to_message_out(assistant),
        )
