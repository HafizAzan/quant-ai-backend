from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.portfolio import (
    AssetDetailOut,
    DashboardSnapshotOut,
    PerformanceSeriesOut,
    PortfolioOverviewOut,
)
from app.services.portfolio_service import PortfolioService
from sqlalchemy.ext.asyncio import AsyncSession

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
portfolio_router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


def get_portfolio_service(session: AsyncSession = Depends(get_db)) -> PortfolioService:
    return PortfolioService(session)


@dashboard_router.get("", response_model=APIResponse[DashboardSnapshotOut])
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> APIResponse[DashboardSnapshotOut]:
    data = await service.get_dashboard(current_user.id)
    return APIResponse(data=data)


@portfolio_router.get("", response_model=APIResponse[PortfolioOverviewOut])
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> APIResponse[PortfolioOverviewOut]:
    data = await service.get_overview(current_user.id)
    return APIResponse(data=data)


@portfolio_router.get("/performance", response_model=APIResponse[PerformanceSeriesOut])
async def get_portfolio_performance(
    range_key: str = Query(default="1M", alias="range", pattern="^(1D|1W|1M|1Y|ALL)$"),
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> APIResponse[PerformanceSeriesOut]:
    data = await service.get_performance(current_user.id, range_key)
    return APIResponse(data=data)


@portfolio_router.get("/holdings/{holding_id}", response_model=APIResponse[AssetDetailOut])
async def get_holding_detail(
    holding_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> APIResponse[AssetDetailOut]:
    data = await service.get_holding_detail(current_user.id, holding_id)
    return APIResponse(data=data)
