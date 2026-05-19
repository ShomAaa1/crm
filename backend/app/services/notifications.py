"""Сервис уведомлений.

Уведомления создаются другими сервисами на ключевые события:
- новая заявка → менеджеру (если назначен), иначе всем менеджерам
- заявка взята в работу → клиенту
- КП отправлено → клиенту
- КП принято/отклонено → менеджеру
- КП на пересчёт → менеджеру
- заказ создан → клиенту
- статус заказа изменён → клиенту
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification
from app.models.enums import NotificationType


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    message: str | None = None,
    n_type: NotificationType = NotificationType.INFO,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id,
        type=n_type,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(n)
    await db.flush()
    return n


async def list_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    only_unread: bool = False,
    limit: int = 50,
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if only_unread:
        q = q.where(Notification.is_read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return list(rows)


async def unread_count(db: AsyncSession, user_id: UUID) -> int:
    q = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id)
        .where(Notification.is_read == False)  # noqa: E712
    )
    return int((await db.execute(q)).scalar_one())


async def mark_as_read(
    db: AsyncSession, user_id: UUID, notification_id: UUID
) -> Notification | None:
    n = (
        await db.execute(
            select(Notification)
            .where(Notification.id == notification_id)
            .where(Notification.user_id == user_id)
        )
    ).scalar_one_or_none()
    if n is None or n.is_read:
        return n
    n.is_read = True
    n.read_at = datetime.now(timezone.utc)
    await db.flush()
    return n


async def mark_all_as_read(db: AsyncSession, user_id: UUID) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id)
        .where(Notification.is_read == False)  # noqa: E712
        .values(is_read=True, read_at=now)
    )
    await db.flush()
    return result.rowcount or 0
