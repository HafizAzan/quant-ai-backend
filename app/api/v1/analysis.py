from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.analysis import (
    AlertDraftOut,
    AnalysisListOut,
    AnalysisOut,
    GenerateAnalysisRequest,
    WorkspaceOut,
)
from app.schemas.common import APIResponse
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["AI Analysis"])


def get_analysis_service(session: AsyncSession = Depends(get_db)) -> AnalysisService:
    return AnalysisService(session)


@router.get("/workspace", response_model=APIResponse[WorkspaceOut])
async def get_workspace(
    symbol: str = Query(default="BTCUSDT", min_length=2, max_length=32),
    timeframe: str = Query(default="1h", pattern="^(1m|5m|15m|1h|4h|1d|1w)$"),
    lookback: int = Query(default=200, ge=20, le=1000),
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> APIResponse[WorkspaceOut]:
    data = await service.get_workspace(current_user.id, symbol, timeframe, lookback)
    return APIResponse(data=data)


@router.post("", response_model=APIResponse[AnalysisOut])
async def generate_analysis(
    payload: GenerateAnalysisRequest,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> APIResponse[AnalysisOut]:
    data = await service.generate(current_user.id, payload)
    return APIResponse(message="Analysis generated", data=data)


@router.get("", response_model=APIResponse[AnalysisListOut])
async def list_analyses(
    saved_only: bool = Query(default=False),
    symbol: str | None = Query(default=None, max_length=32),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> APIResponse[AnalysisListOut]:
    data = await service.list_analyses(
        current_user.id,
        saved_only=saved_only,
        symbol=symbol,
        page=page,
        page_size=page_size,
    )
    return APIResponse(data=data)


@router.get("/{analysis_id}", response_model=APIResponse[AnalysisOut])
async def get_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> APIResponse[AnalysisOut]:
    data = await service.get_analysis(current_user.id, analysis_id)
    return APIResponse(data=data)


@router.post("/{analysis_id}/save", response_model=APIResponse[AnalysisOut])
async def save_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> APIResponse[AnalysisOut]:
    data = await service.save_analysis(current_user.id, analysis_id)
    return APIResponse(message="Analysis saved", data=data)


@router.delete("/{analysis_id}", response_model=APIResponse[dict])
async def delete_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> APIResponse[dict]:
    data = await service.delete_analysis(current_user.id, analysis_id)
    return APIResponse(message="Analysis deleted", data=data)


@router.post("/{analysis_id}/alert-draft", response_model=APIResponse[AlertDraftOut])
async def create_alert_draft(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> APIResponse[AlertDraftOut]:
    data = await service.alert_draft(current_user.id, analysis_id)
    return APIResponse(message="Alert draft ready", data=data)
