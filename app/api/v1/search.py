from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.search import (
    SearchPinCreateRequest,
    SearchPinOut,
    SearchRecentCreateRequest,
    SearchRecentOut,
    SearchResultsOut,
)
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


def get_search_service(session: AsyncSession = Depends(get_db)) -> SearchService:
    return SearchService(session)


@router.get("", response_model=APIResponse[SearchResultsOut])
async def search(
    q: str = Query(default="", max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
) -> APIResponse[SearchResultsOut]:
    return APIResponse(data=await service.search(current_user.id, q, limit=limit))


@router.get("/recents", response_model=APIResponse[list[SearchRecentOut]])
async def list_recents(
    current_user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
) -> APIResponse[list[SearchRecentOut]]:
    return APIResponse(data=await service.list_recents(current_user.id))


@router.post("/recents", response_model=APIResponse[SearchRecentOut])
async def add_recent(
    payload: SearchRecentCreateRequest,
    current_user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
) -> APIResponse[SearchRecentOut]:
    return APIResponse(data=await service.add_recent(current_user.id, payload))


@router.get("/pins", response_model=APIResponse[list[SearchPinOut]])
async def list_pins(
    current_user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
) -> APIResponse[list[SearchPinOut]]:
    return APIResponse(data=await service.list_pins(current_user.id))


@router.post("/pins", response_model=APIResponse[SearchPinOut])
async def add_pin(
    payload: SearchPinCreateRequest,
    current_user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
) -> APIResponse[SearchPinOut]:
    return APIResponse(data=await service.add_pin(current_user.id, payload))


@router.delete("/pins/{item_id}", response_model=APIResponse[None])
async def remove_pin(
    item_id: str,
    current_user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
) -> APIResponse[None]:
    await service.remove_pin(current_user.id, item_id)
    return APIResponse(message="Pin removed", data=None)
