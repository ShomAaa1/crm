"""Эндпоинты заказов."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.middleware.problem import ProblemException
from app.models import User
from app.models.enums import OrderStatus, UserRole
from app.schemas.common import Page
from app.schemas.order import (
    OrderDetail,
    OrderItemOut,
    OrderListItem,
    OrderStatusChangeIn,
    OrderUpdateIn,
)
from app.services import orders as svc
from app.services.audit import log_action

router = APIRouter(prefix="/orders", tags=["orders"])

manager_or_above = require_role(UserRole.MANAGER, UserRole.HEAD, UserRole.ADMIN)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _build_detail(db: AsyncSession, order_id: UUID) -> OrderDetail:
    order = await svc.get_order(db, order_id)
    if order is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заказ не найден",
        )
    pairs = await svc.load_items(db, order.id)
    items = [
        OrderItemOut(
            id=oi.id,
            part_id=oi.part_id,
            article=p.article if p else None,
            name=p.name if p else None,
            quantity=oi.quantity,
            unit_price=oi.unit_price,
            total_price=oi.total_price,
        )
        for oi, p in pairs
    ]
    # Подтягиваем client/manager/cp
    from sqlalchemy import select
    from app.models import Client, Manager, CommercialProposal

    client = (
        await db.execute(select(Client).where(Client.id == order.client_id))
    ).scalar_one_or_none()
    manager_name = None
    if order.manager_id:
        from app.models import User as UserM

        manager_name = (
            await db.execute(
                select(UserM.full_name)
                .join(Manager, Manager.user_id == UserM.id)
                .where(Manager.id == order.manager_id)
            )
        ).scalar_one_or_none()
    cp_number = None
    if order.cp_id:
        cp_number = (
            await db.execute(
                select(CommercialProposal.cp_number).where(
                    CommercialProposal.id == order.cp_id
                )
            )
        ).scalar_one_or_none()

    return OrderDetail(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        client_id=order.client_id,
        client_company=client.company_name if client else None,
        manager_id=order.manager_id,
        manager_name=manager_name,
        cp_id=order.cp_id,
        cp_number=cp_number,
        items_count=len(items),
        total_amount=order.total_amount,
        delivery_address=order.delivery_address,
        payment_terms=order.payment_terms,
        tracking_number=order.tracking_number,
        created_at=order.created_at,
        delivered_at=order.delivered_at,
        items=items,
    )


@router.get("", response_model=Page[OrderListItem])
async def list_orders(
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[OrderListItem]:
    rows, total = await svc.list_for_user(
        db, user, status=status_filter, limit=limit, offset=offset
    )
    items = [
        OrderListItem(
            id=r["order"].id,
            order_number=r["order"].order_number,
            status=r["order"].status,
            client_id=r["order"].client_id,
            client_company=r["client_company"],
            manager_id=r["order"].manager_id,
            manager_name=r["manager_name"],
            cp_id=r["order"].cp_id,
            cp_number=r["cp_number"],
            items_count=r["items_count"],
            total_amount=r["order"].total_amount,
            delivery_address=r["order"].delivery_address,
            tracking_number=r["order"].tracking_number,
            created_at=r["order"].created_at,
            delivered_at=r["order"].delivered_at,
        )
        for r in rows
    ]
    return Page[OrderListItem](items=items, total=total, limit=limit, offset=offset)


@router.get("/by-cp/{cp_id}", response_model=OrderDetail | None)
async def get_by_cp(
    cp_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderDetail | None:
    order = await svc.get_order_by_cp(db, cp_id)
    if order is None:
        return None
    if not await svc.can_access(db, user, order):
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа",
        )
    return await _build_detail(db, order.id)


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderDetail:
    order = await svc.get_order(db, order_id)
    if order is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заказ не найден",
        )
    if not await svc.can_access(db, user, order):
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа",
        )
    return await _build_detail(db, order_id)


@router.patch("/{order_id}", response_model=OrderDetail)
async def update_order(
    order_id: UUID,
    payload: OrderUpdateIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_above),
) -> OrderDetail:
    order = await svc.get_order(db, order_id)
    if order is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заказ не найден",
        )
    if not await svc.can_access(db, actor, order):
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа",
        )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="Нет полей для обновления",
        )

    await svc.update_order(db, order, **data)
    await log_action(
        db,
        user_id=actor.id,
        action="order.update",
        entity_type="order",
        entity_id=order.id,
        details=data,
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, order_id)


@router.post("/{order_id}/status", response_model=OrderDetail)
async def change_order_status(
    order_id: UUID,
    payload: OrderStatusChangeIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_above),
) -> OrderDetail:
    order = await svc.get_order(db, order_id)
    if order is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заказ не найден",
        )
    if not await svc.can_access(db, actor, order):
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа",
        )

    old_status = order.status.value
    try:
        await svc.change_status(db, order, payload.status)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=actor.id,
        action="order.status_change",
        entity_type="order",
        entity_id=order.id,
        details={
            "order_number": order.order_number,
            "from": old_status,
            "to": payload.status.value,
            "reason": payload.reason,
        },
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, order_id)
