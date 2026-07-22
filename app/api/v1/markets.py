from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import safe_decode_token
from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import APIResponse
from app.schemas.market import CandlesData, FavoriteToggleOut, MarketsListData, MarketsMetaOut
from app.services.market_service import MarketService

router = APIRouter(prefix="/markets", tags=["Markets"])
bearer_scheme = HTTPBearer(auto_error=False)


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> UUID | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    payload = safe_decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access" or not payload.get("sub"):
        return None
    user = await UserRepository(session).get_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        return None
    return user.id


def get_market_service(session: AsyncSession = Depends(get_db)) -> MarketService:
    return MarketService(session)


@router.get("", response_model=APIResponse[MarketsListData])
async def list_markets(
    tab: str = Query(default="all", pattern="^(all|favorites|crypto-ai|high-volume|new-listing)$"),
    category: str = Query(default="all", pattern="^(all|crypto|stocks|forex)$"),
    change: str = Query(default="any", pattern="^(any|up|down)$"),
    search: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: UUID | None = Depends(get_optional_user_id),
    service: MarketService = Depends(get_market_service),
) -> APIResponse[MarketsListData]:
    data = await service.list_markets(
        tab=tab,
        category=category,
        change=change,
        search=search,
        page=page,
        page_size=page_size,
        user_id=user_id,
    )
    return APIResponse(data=data)


@router.get("/meta", response_model=APIResponse[MarketsMetaOut])
async def markets_meta(
    service: MarketService = Depends(get_market_service),
) -> APIResponse[MarketsMetaOut]:
    data = await service.get_meta()
    return APIResponse(data=data)


@router.post("/{asset_id}/favorite", response_model=APIResponse[FavoriteToggleOut])
async def toggle_favorite(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MarketService = Depends(get_market_service),
) -> APIResponse[FavoriteToggleOut]:
    data = await service.toggle_favorite(current_user.id, asset_id)
    return APIResponse(message="Favorite updated", data=data)


candles_router = APIRouter(tags=["Markets"])


@candles_router.get("/candles", response_model=APIResponse[CandlesData])
async def get_candles(
    symbol: str = Query(..., min_length=2, max_length=32, description="BTCUSDT or BTC"),
    timeframe: str = Query(default="1h", min_length=2, max_length=8),
    limit: int = Query(default=200, ge=1, le=1000),
    service: MarketService = Depends(get_market_service),
) -> APIResponse[CandlesData]:
    data = await service.get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
    return APIResponse(data=data)
