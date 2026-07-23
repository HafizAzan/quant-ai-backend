from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.paper import (
    AskAiOut,
    AskAiRequest,
    EquityCurveOut,
    PaperDeskOut,
    PlaceOrderOut,
    PlaceOrderRequest,
    PositionDetailOut,
    SentinelActionRequest,
    SetLearningModeRequest,
    TradePreviewOut,
)
from app.services.paper_service import PaperTradingService

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])


def get_paper_service(session: AsyncSession = Depends(get_db)) -> PaperTradingService:
    return PaperTradingService(session)


@router.get("", response_model=APIResponse[PaperDeskOut])
async def get_paper_desk(
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[PaperDeskOut]:
    await service.match_pending_limits(current_user.id)
    data = await service.get_desk(current_user.id)
    return APIResponse(data=data)


@router.get("/equity", response_model=APIResponse[EquityCurveOut])
async def get_equity_curve(
    range_key: str = Query(default="1D", alias="range", pattern="^(1D|1W|1M|ALL)$"),
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[EquityCurveOut]:
    data = await service.get_equity(current_user.id, range_key)
    return APIResponse(data=data)


@router.post("/orders/preview", response_model=APIResponse[TradePreviewOut])
async def preview_order(
    payload: PlaceOrderRequest,
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[TradePreviewOut]:
    data = await service.preview_order(current_user.id, payload)
    return APIResponse(data=data)


@router.post("/orders", response_model=APIResponse[PlaceOrderOut])
async def place_order(
    payload: PlaceOrderRequest,
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[PlaceOrderOut]:
    data = await service.place_order(current_user.id, payload)
    return APIResponse(message=data.message, data=data)


@router.post("/orders/{order_id}/cancel", response_model=APIResponse[PlaceOrderOut])
async def cancel_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[PlaceOrderOut]:
    data = await service.cancel_order(current_user.id, order_id)
    return APIResponse(message=data.message, data=data)


@router.post("/positions/{position_id}/close", response_model=APIResponse[PlaceOrderOut])
async def close_position(
    position_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[PlaceOrderOut]:
    data = await service.close_position(current_user.id, position_id)
    return APIResponse(message=data.message, data=data)


@router.get("/positions/{position_id}", response_model=APIResponse[PositionDetailOut])
async def get_position_detail(
    position_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[PositionDetailOut]:
    data = await service.get_position_detail(current_user.id, position_id)
    return APIResponse(data=data)


@router.patch("/mode", response_model=APIResponse[dict])
async def set_learning_mode(
    payload: SetLearningModeRequest,
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[dict]:
    data = await service.set_learning_mode(current_user.id, payload.mode)
    return APIResponse(message="Learning mode updated", data=data)


@router.post("/ask-ai", response_model=APIResponse[AskAiOut])
async def ask_ai(
    payload: AskAiRequest,
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[AskAiOut]:
    data = await service.ask_ai(current_user.id, payload)
    return APIResponse(data=data)


@router.post("/sentinel", response_model=APIResponse[dict])
async def sentinel_action(
    payload: SentinelActionRequest,
    current_user: User = Depends(get_current_user),
    service: PaperTradingService = Depends(get_paper_service),
) -> APIResponse[dict]:
    data = await service.sentinel_action(current_user.id, payload.action)
    return APIResponse(message="Sentinel updated", data=data)
