from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings


class ChatAgent:
    """Chat/analysis agent.

    Provider priority (LLM_PROVIDER=auto):
      1. OPENAI_API_KEY  → OpenAI-compatible /chat/completions
      2. CURSOR_API_KEY  → Cursor SDK Agent.prompt
    """

    name = "chat"

    def __init__(self, *, temperature: float = 0.45, model: str | None = None) -> None:
        self.temperature = temperature
        self._model_override = model

    @property
    def provider(self) -> str | None:
        return settings.resolved_llm_provider

    @property
    def llm_enabled(self) -> bool:
        return self.provider is not None

    @property
    def model(self) -> str:
        if self._model_override:
            return self._model_override
        if self.provider == "cursor":
            return settings.cursor_model
        return settings.openai_model

    async def reply(self, user_message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        if not self.llm_enabled:
            return self._heuristic(user_message, context)
        try:
            if self.provider == "cursor":
                text = await self._cursor_reply(user_message, context)
            else:
                text = await self._openai_reply(user_message, context)
            return {"content": text, "engine": "llm", "provider": self.provider, "model": self.model}
        except Exception as exc:  # noqa: BLE001
            heuristic = self._heuristic(user_message, context)
            heuristic["fallback_error"] = str(exc)[:300]
            return heuristic

    async def _openai_reply(self, user_message: str, context: dict[str, Any]) -> str:
        system = (
            "You are QuantAI, a concise trading copilot. "
            "Give actionable market insight, risk warnings, and next steps. "
            "Never invent live prices; if unknown, say so."
        )
        if context:
            system += f"\nContext: {context}"
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(f"{settings.openai_base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()

    async def _cursor_reply(self, user_message: str, context: dict[str, Any]) -> str:
        from cursor_sdk import AgentOptions, AsyncAgent, AsyncClient, LocalAgentOptions

        cwd = settings.cursor_cwd or str(Path(__file__).resolve().parents[3])
        prompt = (
            "You are QuantAI, a concise trading copilot. "
            "Reply with trading advice only — no code edits, no file changes, no shell commands. "
            "Give actionable insight, risk warnings, and next steps. "
            "Never invent live prices; if unknown, say so.\n"
            f"Context: {context}\n"
            f"User question: {user_message}"
        )
        async with await AsyncClient.launch_bridge(workspace=cwd) as client:
            result = await AsyncAgent.prompt(
                prompt,
                AgentOptions(
                    api_key=settings.cursor_api_key,
                    model=self.model,
                    local=LocalAgentOptions(cwd=cwd),
                ),
                client=client,
            )
        text = getattr(result, "result", None) or getattr(result, "text", None) or str(result)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Cursor agent returned empty result")
        return text.strip()

    def _heuristic(self, user_message: str, context: dict[str, Any]) -> dict[str, Any]:
        msg = user_message.lower()
        symbol = context.get("symbol") or "BTCUSDT"
        if "risk" in msg or "drawdown" in msg:
            content = (
                f"Risk check for {symbol}: size positions so a single loss stays inside your daily drawdown "
                "budget. Prefer defined stop-loss and avoid stacking correlated exposure."
            )
        elif "analyze" in msg or "chart" in msg:
            content = (
                f"Structure read on {symbol}: watch higher-timeframe trend, wait for pullback into value, "
                "and confirm with volume before entry. I can open AI Analysis for a full breakdown."
            )
        else:
            content = (
                f"Understood: “{user_message[:180]}”. "
                "I can help with analysis, alerts, paper/live risk checks, or strategy ideas. "
                "Set CURSOR_API_KEY or OPENAI_API_KEY for full LLM replies."
            )
        return {"content": content, "engine": "heuristic", "model": "rules-v1"}
