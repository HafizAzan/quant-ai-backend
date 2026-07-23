from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import CHANNEL_NOTIFICATIONS, publish_json
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import CreateNotificationRequest, NotificationOut, NotificationsListOut


def _to_out(row: Notification) -> NotificationOut:
    return NotificationOut(
        id=row.id,
        kind=row.kind,
        title=row.title,
        body=row.body,
        icon=row.icon,
        href=row.href,
        source_type=row.source_type,
        source_id=row.source_id,
        meta=row.meta or {},
        read_at=row.read_at,
        created_at=row.created_at,
        is_read=row.read_at is not None,
    )


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def list_notifications(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> NotificationsListOut:
        items, total = await self.repo.list_for_user(
            user_id, unread_only=unread_only, page=page, page_size=page_size
        )
        unread = await self.repo.unread_count(user_id)
        return NotificationsListOut(
            items=[_to_out(i) for i in items],
            unread_count=unread,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def create(
        self,
        user_id: UUID,
        *,
        kind: str,
        title: str,
        body: str = "",
        icon: str = "trending",
        href: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        meta: dict | None = None,
        publish: bool = True,
    ) -> NotificationOut:
        row = Notification(
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            icon=icon,
            href=href,
            source_type=source_type,
            source_id=source_id,
            meta=meta or {},
        )
        await self.repo.add(row)
        out = _to_out(row)
        if publish:
            publish_json(
                CHANNEL_NOTIFICATIONS,
                json.dumps(
                    {
                        "type": "notification.created",
                        "user_id": str(user_id),
                        "notification": out.model_dump(mode="json"),
                    }
                ),
            )
        return out

    async def create_from_request(self, user_id: UUID, payload: CreateNotificationRequest) -> NotificationOut:
        return await self.create(
            user_id,
            kind=payload.kind,
            title=payload.title,
            body=payload.body,
            icon=payload.icon,
            href=payload.href,
        )

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> NotificationOut:
        row = await self.repo.mark_read(user_id, notification_id, datetime.now(timezone.utc))
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        return _to_out(row)

    async def mark_all_read(self, user_id: UUID) -> int:
        return await self.repo.mark_all_read(user_id, datetime.now(timezone.utc))

    async def dismiss(self, user_id: UUID, notification_id: UUID) -> None:
        row = await self.repo.get(user_id, notification_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        await self.repo.delete(row)
