"""Эндпоинты задач (корректирующих действий) — UC-10 / ФТ-10-02."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.middleware.problem import ProblemException
from app.models import Manager, Task, User
from app.models.enums import TaskStatus, UserRole
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services import tasks as svc
from app.services.audit import log_action

router = APIRouter(prefix="/tasks", tags=["tasks"])

head_or_admin = require_role(UserRole.HEAD, UserRole.ADMIN)


def _ip(req: Request) -> str | None:
    return req.client.host if req.client else None


async def _to_out(db: AsyncSession, task: Task) -> TaskOut:
    manager_name = (
        await db.execute(
            select(User.full_name)
            .join(Manager, Manager.user_id == User.id)
            .where(Manager.id == task.manager_id)
        )
    ).scalar_one_or_none()

    assigned_by_name = None
    if task.assigned_by:
        assigned_by_name = (
            await db.execute(
                select(User.full_name).where(User.id == task.assigned_by)
            )
        ).scalar_one_or_none()

    return TaskOut(
        id=task.id,
        manager_id=task.manager_id,
        manager_name=manager_name,
        assigned_by=task.assigned_by,
        assigned_by_name=assigned_by_name,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        due_date=task.due_date,
        completed_at=task.completed_at,
        created_at=task.created_at,
        is_overdue=svc.is_overdue(task),
    )


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(head_or_admin),
) -> TaskOut:
    manager = (
        await db.execute(select(Manager).where(Manager.id == payload.manager_id))
    ).scalar_one_or_none()
    if manager is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Менеджер не найден",
        )

    try:
        task = await svc.create_task(
            db,
            manager=manager,
            assigned_by=actor,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            due_date=payload.due_date,
        )
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=actor.id,
        action="task.create",
        entity_type="task",
        entity_id=task.id,
        details={"manager_id": str(manager.id), "title": task.title},
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(task)
    return await _to_out(db, task)


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    only_mine: bool = Query(default=False, description="Только мои задачи (для менеджера)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TaskOut]:
    q = select(Task)

    if user.role == UserRole.MANAGER:
        manager = (
            await db.execute(select(Manager).where(Manager.user_id == user.id))
        ).scalar_one_or_none()
        if manager is None:
            return []
        q = q.where(Task.manager_id == manager.id)
    elif user.role in (UserRole.HEAD, UserRole.ADMIN):
        if only_mine:
            # head/admin → "мои" = поставленные мной
            q = q.where(Task.assigned_by == user.id)
    else:
        # клиенту задачи недоступны
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа",
        )

    if status_filter is not None:
        q = q.where(Task.status == status_filter)

    q = q.order_by(Task.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return [await _to_out(db, t) for t in rows]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskOut:
    task = (
        await db.execute(select(Task).where(Task.id == task_id))
    ).scalar_one_or_none()
    if task is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Задача не найдена",
        )

    if user.role == UserRole.MANAGER:
        manager = (
            await db.execute(select(Manager).where(Manager.user_id == user.id))
        ).scalar_one_or_none()
        if manager is None or task.manager_id != manager.id:
            raise ProblemException(
                status_code=status.HTTP_403_FORBIDDEN,
                title="Forbidden",
                detail="Нет доступа к этой задаче",
            )
    elif user.role == UserRole.CLIENT:
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа",
        )

    return await _to_out(db, task)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(head_or_admin),
) -> TaskOut:
    task = (
        await db.execute(select(Task).where(Task.id == task_id))
    ).scalar_one_or_none()
    if task is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Задача не найдена",
        )

    await svc.update_task(
        db,
        task,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        status=payload.status,
    )
    await log_action(
        db,
        user_id=actor.id,
        action="task.update",
        entity_type="task",
        entity_id=task.id,
        details=payload.model_dump(exclude_none=True, mode="json"),
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(task)
    return await _to_out(db, task)


@router.post("/{task_id}/complete", response_model=TaskOut)
async def complete_task(
    task_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskOut:
    if user.role != UserRole.MANAGER:
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Выполнить задачу может только её исполнитель",
        )

    task = (
        await db.execute(select(Task).where(Task.id == task_id))
    ).scalar_one_or_none()
    if task is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Задача не найдена",
        )

    manager = (
        await db.execute(select(Manager).where(Manager.user_id == user.id))
    ).scalar_one_or_none()
    if manager is None:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="У пользователя нет записи менеджера",
        )

    try:
        await svc.complete_task(db, task, manager)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=user.id,
        action="task.complete",
        entity_type="task",
        entity_id=task.id,
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(task)
    return await _to_out(db, task)
