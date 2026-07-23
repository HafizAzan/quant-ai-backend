from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.live import (
    AskAiOut,
    AskAiRequest,
    EmergencyStopOut,
    EmergencyStopRequest,
    LiveDeskOut,
    LiveSettingsRequest,
    PlaceLiveOrderOut,
    PlaceLiveOrderRequest,
    PositionActionRequest,
    PositionDetailOut,
    SetAutoTradingRequest,
    TradePreviewOut,
)
from app.services.live_service import LiveTradingService

router = APIRouter(prefix="/live-trading", tags=["Live Trading"])


def get_live_service(session: AsyncSession = Depends(get_db)) -> LiveTradingService:
    return LiveTradingService(session)


@router.get("", response_model=APIResponse[LiveDeskOut])
async def get_live_desk(
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[LiveDeskOut]:
    data = await service.get_desk(current_user.id)
    return APIResponse(data=data)


@router.get("/positions/{position_id}", response_model=APIResponse[PositionDetailOut])
async def get_position_detail(
    position_id: UUID,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[PositionDetailOut]:
    data = await service.get_position_detail(current_user.id, position_id)
    return APIResponse(data=data)


@router.post("/auto-trading", response_model=APIResponse[LiveDeskOut])
async def set_auto_trading(
    payload: SetAutoTradingRequest,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[LiveDeskOut]:
    data = await service.set_auto_trading(current_user.id, payload)
    return APIResponse(message="Auto trading updated", data=data)


@router.patch("/settings", response_model=APIResponse[LiveDeskOut])
async def update_settings(
    payload: LiveSettingsRequest,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[LiveDeskOut]:
    data = await service.update_settings(current_user.id, payload)
    return APIResponse(message="Settings updated", data=data)


@router.post("/orders/preview", response_model=APIResponse[TradePreviewOut])
async def preview_order(
    payload: PlaceLiveOrderRequest,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[TradePreviewOut]:
    data = await service.preview(current_user.id, payload)
    return APIResponse(data=data)


@router.post("/orders", response_model=APIResponse[PlaceLiveOrderOut])
async def place_order(
    payload: PlaceLiveOrderRequest,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[PlaceLiveOrderOut]:
    data = await service.place_order(current_user.id, payload)
    return APIResponse(message=data.message, data=data)


@router.post("/orders/{order_id}/cancel", response_model=APIResponse[PlaceLiveOrderOut])
async def cancel_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[PlaceLiveOrderOut]:
    data = await service.cancel_order(current_user.id, order_id)
    return APIResponse(message=data.message, data=data)


@router.post("/orders/cancel-all", response_model=APIResponse[PlaceLiveOrderOut])
async def cancel_all_orders(
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[PlaceLiveOrderOut]:
    data = await service.cancel_all_orders(current_user.id)
    return APIResponse(message=data.message, data=data)


@router.post("/positions/{position_id}/action", response_model=APIResponse[PlaceLiveOrderOut])
async def position_action(
    position_id: UUID,
    payload: PositionActionRequest,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[PlaceLiveOrderOut]:
    data = await service.position_action(current_user.id, position_id, payload)
    return APIResponse(message=data.message, data=data)


@router.post("/emergency", response_model=APIResponse[EmergencyStopOut])
async def emergency_stop(
    payload: EmergencyStopRequest,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[EmergencyStopOut]:
    data = await service.emergency(current_user.id, payload)
    return APIResponse(message=data.message, data=data)


@router.post("/ask-ai", response_model=APIResponse[AskAiOut])
async def ask_ai(
    payload: AskAiRequest,
    current_user: User = Depends(get_current_user),
    service: LiveTradingService = Depends(get_live_service),
) -> APIResponse[AskAiOut]:
    data = await service.ask_ai(current_user.id, payload)
    return APIResponse(data=data)
