"""Эндпоинты для работы со списком менеджеров (для назначения заявок)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models import Manager, Request, User
from app.models.enums import RequestStatus, UserRole

router = APIRouter(prefix="/managers", tags=["managers"])

head_or_admin = require_role(UserRole.HEAD, UserRole.ADMIN)


class ManagerAvailability(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    specialization: str | None = None
    department: str | None = None
    is_available: bool
    active_requests_count: int


# Заявки в этих статусах считаются "активной нагрузкой" менеджера.
ACTIVE_STATUSES = (
    RequestStatus.NEW,
    RequestStatus.IN_PROGRESS,
    RequestStatus.CP_SENT,
    RequestStatus.REVISION_NEEDED,
)


@router.get("/available", response_model=list[ManagerAvailability])
async def list_available_managers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(head_or_admin),
) -> list[ManagerAvailability]:
    """Список менеджеров с указанием специализации и текущей нагрузки.

    Используется руководителем при назначении заявки (UC-11, ФТ-11-01/02).
    """
    # Считаем активные заявки на каждого менеджера одним запросом.
    load_subq = (
        select(
            Request.manager_id.label("mid"),
            func.count().label("cnt"),
        )
        .where(Request.status.in_(ACTIVE_STATUSES))
        .where(Request.manager_id.is_not(None))
        .group_by(Request.manager_id)
        .subquery()
    )

    rows = (
        await db.execute(
            select(
                Manager.id,
                Manager.user_id,
                User.full_name,
                Manager.specialization,
                Manager.department,
                Manager.is_available,
                func.coalesce(load_subq.c.cnt, 0).label("active_count"),
            )
            .join(User, User.id == Manager.user_id)
            .outerjoin(load_subq, load_subq.c.mid == Manager.id)
            .where(User.is_active.is_(True))
            .order_by(User.full_name)
        )
    ).all()

    return [
        ManagerAvailability(
            id=mid,
            user_id=uid,
            full_name=full_name,
            specialization=spec,
            department=dept,
            is_available=is_available,
            active_requests_count=int(active_count or 0),
        )
        for mid, uid, full_name, spec, dept, is_available, active_count in rows
    ]
