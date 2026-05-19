"""Схемы уведомлений."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    message: str | None = None
    is_read: bool
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None
    created_at: datetime
    read_at: datetime | None = None


class NotificationSummary(BaseModel):
    items: list[NotificationOut]
    unread_count: int
