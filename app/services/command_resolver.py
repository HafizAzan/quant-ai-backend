"""Platform command registry + NL/slash resolver (MVP, no LLM)."""

from __future__ import annotations

import re
from typing import Any

PLATFORM_COMMANDS: list[dict[str, Any]] = [
    {
        "id": "analyze-symbol",
        "label": "Analyze Symbol",
        "description": "Run AI market structure analysis on a symbol",
        "kind": "analyze",
        "module": "ai-analysis",
        "href": "/ai-analysis",
        "slash": "/analyze",
        "param_keys": ["symbol", "timeframe"],
        "examples": ["Analyze BTCUSDT", "Analyze ETH on 4H"],
        "keywords": ["analyze", "analysis", "btcusdt", "ethusdt", "chart analysis"],
    },
    {
        "id": "open-ai-analysis",
        "label": "Open AI Analysis",
        "description": "Navigate to the AI Analysis workspace",
        "kind": "navigate",
        "module": "ai-analysis",
        "href": "/ai-analysis",
        "slash": "/ai-analysis",
        "examples": ["Open AI Analysis", "Go to AI Analysis"],
        "keywords": ["open ai analysis", "ai analysis", "chart workspace"],
    },
    {
        "id": "show-portfolio",
        "label": "Show Portfolio",
        "description": "Open portfolio overview and positions",
        "kind": "navigate",
        "module": "portfolio",
        "href": "/portfolio",
        "slash": "/portfolio",
        "examples": ["Show my Portfolio", "Open portfolio"],
        "keywords": ["portfolio", "show my portfolio", "positions", "holdings"],
    },
    {
        "id": "open-paper-trading",
        "label": "Open Paper Trading",
        "description": "Launch the paper trading desk",
        "kind": "trade",
        "module": "paper-trading",
        "href": "/paper-trading",
        "slash": "/paper",
        "examples": ["Open Paper Trading", "Start paper trade"],
        "keywords": ["paper trading", "paper trade", "simulate"],
    },
    {
        "id": "open-live-trading",
        "label": "Open Live Trading",
        "description": "Open the live execution desk",
        "kind": "trade",
        "module": "live-trading",
        "href": "/live-trading",
        "slash": "/live",
        "examples": ["Open Live Trading"],
        "keywords": ["live trading", "live trade", "execute"],
    },
    {
        "id": "compare-assets",
        "label": "Compare Assets",
        "description": "Compare relative strength and correlation",
        "kind": "compare",
        "module": "market",
        "href": "/market",
        "slash": "/compare",
        "param_keys": ["base", "quote"],
        "examples": ["Compare BTC vs ETH", "BTC vs SOL correlation"],
        "keywords": ["compare", "vs", "versus", "correlation"],
    },
    {
        "id": "find-setup",
        "label": "Find Today's Best Setup",
        "description": "Surface high-probability setups across the watchlist",
        "kind": "setup",
        "module": "ai-analysis",
        "href": "/ai-analysis",
        "slash": "/setup",
        "examples": ["Find today's best setup", "Find long setup", "Find short setup"],
        "keywords": ["best setup", "find setup", "long setup", "short setup", "today's"],
    },
    {
        "id": "create-alert",
        "label": "Create Price Alert",
        "description": "Create a price or condition alert",
        "kind": "alert",
        "module": "alerts",
        "href": "/alerts",
        "slash": "/alert",
        "param_keys": ["symbol", "price"],
        "examples": ["Create a price alert at $100,000", "Alert BTC at 100k"],
        "keywords": ["alert", "price alert", "notify", "100,000", "100k"],
    },
    {
        "id": "backtest-strategy",
        "label": "Backtest Strategy",
        "description": "Open strategy backtesting workspace",
        "kind": "backtest",
        "module": "strategies",
        "href": "/strategies",
        "slash": "/backtest",
        "examples": ["Backtest my strategy", "Run backtest"],
        "keywords": ["backtest", "strategy", "historical"],
    },
    {
        "id": "review-trades",
        "label": "Review Recent Trades",
        "description": "Open journal for recent trade review",
        "kind": "review",
        "module": "journal",
        "href": "/journal",
        "slash": "/review",
        "param_keys": ["count"],
        "examples": ["Review my last 10 trades", "Review journal"],
        "keywords": ["review", "last trades", "journal", "trade history"],
    },
    {
        "id": "open-market",
        "label": "Open Markets",
        "description": "Browse market screener and assets",
        "kind": "navigate",
        "module": "market",
        "href": "/market",
        "slash": "/market",
        "examples": ["Open Markets", "Show market screener"],
        "keywords": ["market", "markets", "screener"],
    },
    {
        "id": "open-dashboard",
        "label": "Open Dashboard",
        "description": "Return to the trading dashboard",
        "kind": "navigate",
        "module": "dashboard",
        "href": "/dashboard",
        "slash": "/dashboard",
        "examples": ["Open Dashboard", "Go home"],
        "keywords": ["dashboard", "home", "overview"],
    },
]

COMMAND_PROMPTS = [
    "Analyze BTCUSDT",
    "Open AI Analysis",
    "Show my Portfolio",
    "Open Paper Trading",
    "Compare BTC vs ETH",
    "Find today's best setup",
    "Create a price alert at $100,000",
    "Backtest my strategy",
    "Review my last 10 trades",
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("$", "").replace(",", " ")).strip()


def extract_symbol(raw: str) -> str | None:
    match = re.search(r"\b([A-Za-z]{2,10})(?:USDT|USD)?\b", raw.upper())
    if not match:
        return None
    token = match.group(1)
    if token in {"VS", "MY", "THE", "AND", "FOR", "OPEN", "SHOW", "FIND"}:
        return None
    if f"{token}USDT" in raw.upper():
        return f"{token}USDT"
    if token in {"BTC", "ETH", "SOL", "LINK"}:
        return f"{token}USDT"
    return token


def extract_price(raw: str) -> float | None:
    match = re.search(r"\$?\s*(\d{4,7}(?:\.\d+)?)\b", raw.replace(",", ""))
    if not match:
        return None
    return float(match.group(1))


def extract_compare_pair(raw: str) -> dict[str, str]:
    match = re.search(r"\b([A-Z]{2,10})\s+VS\.?\s+([A-Z]{2,10})\b", raw.upper())
    if not match:
        return {}
    return {"base": f"{match.group(1)}USDT", "quote": f"{match.group(2)}USDT"}


def score_command(normalized: str, command: dict[str, Any]) -> float:
    score = 0.0
    without_slash = normalized.lstrip("/")
    slash = command.get("slash")
    if slash:
        slash_key = slash.lstrip("/").lower()
        if without_slash == slash_key or without_slash.startswith(f"{slash_key} ") or normalized == slash.lower():
            score += 0.9
    for keyword in command.get("keywords", []):
        if keyword in normalized or keyword in without_slash:
            score += 0.35 if len(keyword) > 8 else 0.25
    for example in command.get("examples", []):
        example_norm = normalize(example)
        if normalized == example_norm or without_slash == example_norm:
            score += 0.8
        elif example_norm in normalized or normalized in example_norm:
            score += 0.4
    return min(score, 1.0)


def build_params(raw: str, command: dict[str, Any]) -> dict[str, str | float | int]:
    params: dict[str, str | float | int] = {}
    keys = command.get("param_keys") or []
    if "symbol" in keys:
        symbol = extract_symbol(raw)
        if symbol:
            params["symbol"] = symbol
    if "price" in keys:
        price = extract_price(raw)
        if price is not None:
            params["price"] = price
    if "base" in keys or "quote" in keys:
        pair = extract_compare_pair(raw)
        params.update(pair)
    if "count" in keys:
        count_match = re.search(r"\blast\s+(\d+)\b", raw, re.I)
        if count_match:
            params["count"] = int(count_match.group(1))
    if "timeframe" in keys:
        tf = re.search(r"\b(1m|5m|15m|1h|4h|1d|1w)\b", raw, re.I)
        if tf:
            params["timeframe"] = tf.group(1).lower()
    return params


def build_summary(intent: dict[str, Any]) -> str:
    label = intent["label"]
    params = intent.get("params") or {}
    kind = intent["kind"]
    parts = [f"Recognized platform command: {label}."]
    if params.get("symbol"):
        parts.append(f"Symbol context: {params['symbol']}.")
    if params.get("base") and params.get("quote"):
        parts.append(f"Comparison: {params['base']} vs {params['quote']}.")
    if params.get("price") is not None:
        parts.append(f"Alert level: ${float(params['price']):,.0f}.")
    if params.get("count"):
        parts.append(f"Review window: last {params['count']} trades.")
    if params.get("timeframe"):
        parts.append(f"Timeframe: {params['timeframe']}.")
    if kind in {"navigate", "trade", "review", "backtest"}:
        parts.append("Ready to open the target workspace.")
    else:
        parts.append("Command center can hand this off to the matching AI module.")
    return " ".join(parts)


def resolve_platform_command(raw: str) -> dict[str, Any] | None:
    normalized = normalize(raw)
    if not normalized:
        return None
    best: dict[str, Any] | None = None
    best_score = 0.0
    for command in PLATFORM_COMMANDS:
        score = score_command(normalized, command)
        if score > best_score:
            best = command
            best_score = score
    if best is None or best_score < 0.35:
        return None
    return {
        "command_id": best["id"],
        "kind": best["kind"],
        "module": best["module"],
        "href": best["href"],
        "label": best["label"],
        "raw": raw,
        "confidence": round(best_score, 2),
        "params": build_params(raw, best),
    }


def to_execution_result(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent": intent,
        "status": "ready",
        "summary": build_summary(intent),
        "cta_label": f"Open {intent['label']}",
        "cta_href": intent["href"],
    }


def filter_platform_commands(query: str) -> list[dict[str, Any]]:
    q = normalize(query.lstrip("/"))
    if not q:
        return list(PLATFORM_COMMANDS)
    out: list[dict[str, Any]] = []
    for command in PLATFORM_COMMANDS:
        haystack = " ".join(
            [
                command["id"],
                command["label"],
                command.get("slash") or "",
                *command.get("keywords", []),
                *command.get("examples", []),
            ]
        ).lower()
        if q in haystack:
            out.append(command)
    return out
