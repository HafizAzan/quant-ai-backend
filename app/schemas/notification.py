from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    title: str
    body: str
    icon: str
    href: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    read_at: datetime | None = None
    created_at: datetime
    is_read: bool = False


class NotificationsListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int
    page: int
    page_size: int
    total: int


class CreateNotificationRequest(BaseModel):
    kind: str = Field(default="system", max_length=32)
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(default="", max_length=2000)
    icon: str = Field(default="trending", max_length=32)
    href: str | None = Field(default=None, max_length=255)
