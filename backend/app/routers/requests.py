"""Эндпоинты заявок (requests)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.middleware.problem import ProblemException
from app.models import Client, Manager, User
from app.models.enums import RequestStatus, UserRole
from app.schemas.common import Page
from app.schemas.request import (
    RequestCreate,
    RequestDetail,
    RequestItemOut,
    RequestListItem,
    StatusChangeIn,
)
from app.services import requests as svc
from app.services.audit import log_action

router = APIRouter(prefix="/requests", tags=["requests"])

client_only = require_role(UserRole.CLIENT)
manager_or_above = require_role(UserRole.MANAGER, UserRole.HEAD, UserRole.ADMIN)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _to_list_item(row: dict) -> RequestListItem:
    r = row["request"]
    return RequestListItem(
        id=r.id,
        request_number=r.request_number,
        status=r.status,
        client_id=r.client_id,
        client_company=row["client_company"],
        manager_id=r.manager_id,
        manager_name=row["manager_name"],
        items_count=row["items_count"],
        total=row["total"],
        comment=r.comment,
        created_at=r.created_at,
        taken_at=r.taken_at,
        sla_deadline=r.sla_deadline,
        closed_at=r.closed_at,
        sla_overdue=row["sla_overdue"],
    )


@router.post("", response_model=RequestDetail, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: RequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> RequestDetail:
    client = (
        await db.execute(select(Client).where(Client.user_id == user.id))
    ).scalar_one_or_none()
    if client is None:
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Пользователь не привязан к клиенту",
        )

    try:
        new_request = await svc.create_from_cart(db, client, payload.comment)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=user.id,
        action="request.create",
        entity_type="request",
        entity_id=new_request.id,
        details={"request_number": new_request.request_number},
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(new_request)
    return await _build_detail(db, user, new_request.id)


@router.get("", response_model=Page[RequestListItem])
async def list_requests(
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    scope: str | None = Query(
        default=None,
        pattern="^(mine|unassigned)$",
        description="Только для роли manager: mine=мои в работе, unassigned=новые без менеджера",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[RequestListItem]:
    rows, total = await svc.list_for_user(
        db,
        user,
        status=status_filter,
        only_mine=scope == "mine",
        only_unassigned=scope == "unassigned",
        limit=limit,
        offset=offset,
    )
    return Page[RequestListItem](
        items=[_to_list_item(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


async def _build_detail(
    db: AsyncSession, user: User, request_id: UUID
) -> RequestDetail:
    r = await svc.get_request(db, request_id)
    if r is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заявка не найдена",
        )
    if not await svc.can_access(db, user, r):
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа к этой заявке",
        )

    pairs = await svc.load_items_with_parts(db, request_id)
    items: list[RequestItemOut] = []
    total = Decimal("0.00")
    for ri, part in pairs:
        line_total = (
            Decimal(ri.price_at_moment) * ri.quantity
            if ri.price_at_moment is not None
            else None
        )
        if line_total is not None:
            total += line_total
        items.append(
            RequestItemOut(
                id=ri.id,
                part_id=ri.part_id,
                article=part.article if part else None,
                name=part.name if part else None,
                description=ri.description,
                quantity=ri.quantity,
                price_at_moment=ri.price_at_moment,
                line_total=line_total,
            )
        )

    # client/company/manager via single query
    client = (
        await db.execute(select(Client).where(Client.id == r.client_id))
    ).scalar_one_or_none()
    manager_name = None
    if r.manager_id:
        mgr_row = (
            await db.execute(
                select(User.full_name)
                .join(Manager, Manager.user_id == User.id)
                .where(Manager.id == r.manager_id)
            )
        ).scalar_one_or_none()
        manager_name = mgr_row

    from datetime import datetime, timezone

    sla_overdue = bool(
        r.sla_deadline
        and r.status in (RequestStatus.NEW, RequestStatus.IN_PROGRESS)
        and r.sla_deadline < datetime.now(timezone.utc)
    )

    return RequestDetail(
        id=r.id,
        request_number=r.request_number,
        status=r.status,
        client_id=r.client_id,
        client_company=client.company_name if client else None,
        manager_id=r.manager_id,
        manager_name=manager_name,
        items_count=len(items),
        total=total,
        comment=r.comment,
        created_at=r.created_at,
        taken_at=r.taken_at,
        sla_deadline=r.sla_deadline,
        closed_at=r.closed_at,
        sla_overdue=sla_overdue,
        items=items,
    )


@router.get("/{request_id}", response_model=RequestDetail)
async def get_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RequestDetail:
    return await _build_detail(db, user, request_id)


@router.post("/{request_id}/take", response_model=RequestDetail)
async def take_request(
    request_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manager_or_above),
) -> RequestDetail:
    r = await svc.get_request(db, request_id)
    if r is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заявка не найдена",
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
        await svc.take_to_work(db, r, manager)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=user.id,
        action="request.take",
        entity_type="request",
        entity_id=r.id,
        details={"request_number": r.request_number},
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, user, request_id)


@router.post("/{request_id}/status", response_model=RequestDetail)
async def change_status(
    request_id: UUID,
    payload: StatusChangeIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manager_or_above),
) -> RequestDetail:
    r = await svc.get_request(db, request_id)
    if r is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заявка не найдена",
        )

    # Менеджер может менять только свои заявки
    if user.role == UserRole.MANAGER:
        manager = (
            await db.execute(select(Manager).where(Manager.user_id == user.id))
        ).scalar_one_or_none()
        if manager is None or r.manager_id != manager.id:
            raise ProblemException(
                status_code=status.HTTP_403_FORBIDDEN,
                title="Forbidden",
                detail="Это не ваша заявка",
            )

    old_status = r.status.value
    try:
        await svc.change_status(db, r, payload.status)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=user.id,
        action="request.status_change",
        entity_type="request",
        entity_id=r.id,
        details={
            "request_number": r.request_number,
            "from": old_status,
            "to": payload.status.value,
            "reason": payload.reason,
        },
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, user, request_id)


@router.post("/{request_id}/cancel", response_model=RequestDetail)
async def cancel_request(
    request_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> RequestDetail:
    r = await svc.get_request(db, request_id)
    if r is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заявка не найдена",
        )
    if not await svc.can_access(db, user, r):
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа к этой заявке",
        )
    try:
        await svc.cancel_by_client(db, r)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=user.id,
        action="request.cancel",
        entity_type="request",
        entity_id=r.id,
        details={"request_number": r.request_number},
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, user, request_id)
