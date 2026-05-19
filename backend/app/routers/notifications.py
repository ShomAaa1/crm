"""Эндпоинты уведомлений."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.problem import ProblemException
from app.models import User
from app.schemas.notification import NotificationOut, NotificationSummary
from app.services import notifications as svc

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationSummary)
async def list_notifications(
    only_unread: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationSummary:
    items = await svc.list_for_user(
        db, user.id, only_unread=only_unread, limit=limit
    )
    unread = await svc.unread_count(db, user.id)
    return NotificationSummary(
        items=[NotificationOut.model_validate(n, from_attributes=True) for n in items],
        unread_count=unread,
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationOut:
    n = await svc.mark_as_read(db, user.id, notification_id)
    if n is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Уведомление не найдено",
        )
    await db.commit()
    return NotificationOut.model_validate(n, from_attributes=True)


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    count = await svc.mark_all_as_read(db, user.id)
    await db.commit()
    return {"marked": count}
