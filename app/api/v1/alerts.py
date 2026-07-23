from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.alert import (
    AlertOut,
    AlertsDeskOut,
    AlertsListOut,
    ChannelTestOut,
    CreateAlertRequest,
    EvaluateAlertsOut,
    SnoozeRequest,
)
from app.schemas.common import APIResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def get_alert_service(session: AsyncSession = Depends(get_db)) -> AlertService:
    return AlertService(session)


@router.get("/desk", response_model=APIResponse[AlertsDeskOut])
async def get_alerts_desk(
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[AlertsDeskOut]:
    data = await service.get_desk(current_user.id)
    return APIResponse(data=data)


@router.get("", response_model=APIResponse[AlertsListOut])
async def list_alerts(
    tab: str = Query(default="all", pattern="^(all|price|technical|ai)$"),
    search: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[AlertsListOut]:
    data = await service.list_alerts(
        current_user.id, tab=tab, search=search, page=page, page_size=page_size
    )
    return APIResponse(data=data)


@router.post("", response_model=APIResponse[AlertOut])
async def create_alert(
    payload: CreateAlertRequest,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[AlertOut]:
    data = await service.create_alert(current_user.id, payload)
    return APIResponse(message="Alert created", data=data)


@router.post("/evaluate", response_model=APIResponse[EvaluateAlertsOut])
async def evaluate_alerts(
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[EvaluateAlertsOut]:
    data = await service.evaluate(current_user.id)
    return APIResponse(message="Evaluation complete", data=data)


@router.get("/{alert_id}", response_model=APIResponse[AlertOut])
async def get_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[AlertOut]:
    data = await service.get_alert(current_user.id, alert_id)
    return APIResponse(data=data)


@router.post("/{alert_id}/toggle", response_model=APIResponse[AlertOut])
async def toggle_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[AlertOut]:
    data = await service.toggle(current_user.id, alert_id)
    return APIResponse(message="Alert updated", data=data)


@router.post("/{alert_id}/mute", response_model=APIResponse[AlertOut])
async def mute_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[AlertOut]:
    data = await service.mute(current_user.id, alert_id)
    return APIResponse(message="Alert muted", data=data)


@router.post("/{alert_id}/snooze", response_model=APIResponse[AlertOut])
async def snooze_alert(
    alert_id: UUID,
    payload: SnoozeRequest,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[AlertOut]:
    data = await service.snooze(current_user.id, alert_id, payload.minutes)
    return APIResponse(message="Alert snoozed", data=data)


@router.post("/{alert_id}/archive", response_model=APIResponse[AlertOut])
async def archive_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[AlertOut]:
    data = await service.archive(current_user.id, alert_id)
    return APIResponse(message="Alert archived", data=data)


@router.delete("/{alert_id}", response_model=APIResponse[dict])
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[dict]:
    data = await service.delete(current_user.id, alert_id)
    return APIResponse(message="Alert deleted", data=data)


@router.post("/channels/{channel_id}/test", response_model=APIResponse[ChannelTestOut])
async def test_channel(
    channel_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
) -> APIResponse[ChannelTestOut]:
    data = await service.test_channel(current_user.id, channel_id)
    return APIResponse(message=data.message, data=data)
