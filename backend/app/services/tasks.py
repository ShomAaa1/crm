"""Сервис задач (корректирующих действий) — UC-10 / ФТ-10-02."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Manager, Task, User
from app.models.enums import NotificationType, TaskStatus
from app.services import notifications as notif_svc


async def create_task(
    db: AsyncSession,
    *,
    manager: Manager,
    assigned_by: User,
    title: str,
    description: str | None,
    priority: str,
    due_date: date | None,
) -> Task:
    if not manager.is_available:
        raise ValueError("Нельзя назначить задачу на недоступного менеджера")

    task = Task(
        manager_id=manager.id,
        assigned_by=assigned_by.id,
        title=title,
        description=description,
        priority=priority,
        status=TaskStatus.PENDING,
        due_date=due_date,
    )
    db.add(task)
    await db.flush()

    # Уведомление менеджеру
    due = f" Срок: {due_date.isoformat()}" if due_date else ""
    await notif_svc.create(
        db,
        user_id=manager.user_id,
        title=f"Новая задача: {title}",
        message=f"Руководитель поставил вам задачу.{due}",
        n_type=NotificationType.INFO,
        related_entity_type="task",
        related_entity_id=task.id,
    )
    return task


async def update_task(
    db: AsyncSession,
    task: Task,
    *,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    due_date: date | None = None,
    status: str | None = None,
) -> Task:
    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if priority is not None:
        task.priority = priority  # type: ignore[assignment]
    if due_date is not None:
        task.due_date = due_date
    if status is not None:
        task.status = status  # type: ignore[assignment]
        if status == TaskStatus.COMPLETED and task.completed_at is None:
            task.completed_at = datetime.now(timezone.utc)
        elif status != TaskStatus.COMPLETED:
            task.completed_at = None
    await db.flush()
    return task


async def complete_task(
    db: AsyncSession, task: Task, manager: Manager
) -> Task:
    """Менеджер помечает задачу выполненной + уведомление руководителю."""
    if task.manager_id != manager.id:
        raise ValueError("Эта задача назначена не вам")
    if task.status == TaskStatus.COMPLETED:
        raise ValueError("Задача уже выполнена")
    if task.status == TaskStatus.CANCELLED:
        raise ValueError("Задача отменена и не может быть выполнена")

    task.status = TaskStatus.COMPLETED  # type: ignore[assignment]
    task.completed_at = datetime.now(timezone.utc)
    await db.flush()

    # Уведомление руководителю (assigned_by)
    if task.assigned_by:
        manager_user = (
            await db.execute(select(User).where(User.id == manager.user_id))
        ).scalar_one_or_none()
        manager_name = manager_user.full_name if manager_user else "Менеджер"
        await notif_svc.create(
            db,
            user_id=task.assigned_by,
            title=f"Задача выполнена: {task.title}",
            message=f"{manager_name} отметил задачу как выполненную.",
            n_type=NotificationType.INFO,
            related_entity_type="task",
            related_entity_id=task.id,
        )

    return task


def is_overdue(task: Task) -> bool:
    if task.due_date is None:
        return False
    if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
        return False
    return task.due_date < datetime.now(timezone.utc).date()
