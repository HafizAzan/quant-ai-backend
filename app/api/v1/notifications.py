from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.notification import CreateNotificationRequest, NotificationOut, NotificationsListOut
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(session: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(session)


@router.get("", response_model=APIResponse[NotificationsListOut])
async def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> APIResponse[NotificationsListOut]:
    data = await service.list_notifications(
        current_user.id, unread_only=unread_only, page=page, page_size=page_size
    )
    return APIResponse(data=data)


@router.post("", response_model=APIResponse[NotificationOut])
async def create_notification(
    payload: CreateNotificationRequest,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> APIResponse[NotificationOut]:
    return APIResponse(message="Notification created", data=await service.create_from_request(current_user.id, payload))


@router.post("/read-all", response_model=APIResponse[dict])
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> APIResponse[dict]:
    count = await service.mark_all_read(current_user.id)
    return APIResponse(message="All marked read", data={"marked": count})


@router.post("/{notification_id}/read", response_model=APIResponse[NotificationOut])
async def mark_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> APIResponse[NotificationOut]:
    return APIResponse(data=await service.mark_read(current_user.id, notification_id))


@router.delete("/{notification_id}", response_model=APIResponse[None])
async def dismiss_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> APIResponse[None]:
    await service.dismiss(current_user.id, notification_id)
    return APIResponse(message="Dismissed", data=None)
