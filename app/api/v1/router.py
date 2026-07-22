from fastapi import APIRouter

from app.api.v1 import auth, health, markets, portfolio

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(markets.router)
api_router.include_router(markets.candles_router)
api_router.include_router(portfolio.dashboard_router)
api_router.include_router(portfolio.portfolio_router)
