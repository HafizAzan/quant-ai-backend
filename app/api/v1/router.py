from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    analysis,
    auth,
    chat,
    exchange,
    health,
    journal,
    live,
    markets,
    notifications,
    paper,
    portfolio,
    search,
    settings,
    strategies,
    ws,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(markets.router)
api_router.include_router(markets.candles_router)
api_router.include_router(portfolio.dashboard_router)
api_router.include_router(portfolio.portfolio_router)
api_router.include_router(paper.router)
api_router.include_router(analysis.router)
api_router.include_router(alerts.router)
api_router.include_router(journal.router)
api_router.include_router(chat.router)
api_router.include_router(chat.commands_router)
api_router.include_router(strategies.router)
api_router.include_router(live.router)
api_router.include_router(settings.router)
api_router.include_router(notifications.router)
api_router.include_router(search.router)
api_router.include_router(exchange.router)
api_router.include_router(ws.router)
