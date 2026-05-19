"""Дашборд для head/admin — агрегированные счётчики."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models import (
    CommercialProposal,
    Order,
    Request,
    User,
)
from app.models.enums import CPStatus, OrderStatus, RequestStatus, UserRole

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

head_or_admin = require_role(UserRole.HEAD, UserRole.ADMIN)


class CounterItem(BaseModel):
    label: str
    value: int


class DashboardSummary(BaseModel):
    requests_by_status: list[CounterItem]
    proposals_by_status: list[CounterItem]
    orders_by_status: list[CounterItem]
    revenue_30d: Decimal
    cp_conversion: float
    total_clients: int
    total_managers: int


REQ_STATUS_LABELS: dict[RequestStatus, str] = {
    RequestStatus.NEW: "Новые",
    RequestStatus.IN_PROGRESS: "В работе",
    RequestStatus.CP_SENT: "КП отправлено",
    RequestStatus.ACCEPTED: "Принято",
    RequestStatus.REJECTED: "Отклонено",
    RequestStatus.REVISION_NEEDED: "Доработка",
    RequestStatus.CLOSED_SUCCESS: "Закрыто успешно",
    RequestStatus.CLOSED_FAIL: "Закрыто неуспешно",
    RequestStatus.CANCELLED: "Отменено",
}

CP_STATUS_LABELS: dict[CPStatus, str] = {
    CPStatus.DRAFT: "Черновики",
    CPStatus.SENT: "Отправлены",
    CPStatus.ACCEPTED: "Приняты",
    CPStatus.REJECTED: "Отклонены",
    CPStatus.EXPIRED: "Истекли",
}

ORD_STATUS_LABELS: dict[OrderStatus, str] = {
    OrderStatus.CREATED: "Созданы",
    OrderStatus.CONFIRMED: "Подтверждены",
    OrderStatus.SHIPPED: "Отгружены",
    OrderStatus.DELIVERED: "Доставлены",
    OrderStatus.CANCELLED: "Отменены",
}


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(head_or_admin),
) -> DashboardSummary:
    # Заявки по статусам
    req_rows = (
        await db.execute(
            select(Request.status, func.count()).group_by(Request.status)
        )
    ).all()
    req_counts = {s: int(c) for s, c in req_rows}
    requests_by_status = [
        CounterItem(label=REQ_STATUS_LABELS[s], value=req_counts.get(s, 0))
        for s in RequestStatus
    ]

    # КП по статусам
    cp_rows = (
        await db.execute(
            select(CommercialProposal.status, func.count()).group_by(
                CommercialProposal.status
            )
        )
    ).all()
    cp_counts = {s: int(c) for s, c in cp_rows}
    proposals_by_status = [
        CounterItem(label=CP_STATUS_LABELS[s], value=cp_counts.get(s, 0))
        for s in CPStatus
    ]

    # Заказы по статусам
    ord_rows = (
        await db.execute(
            select(Order.status, func.count()).group_by(Order.status)
        )
    ).all()
    ord_counts = {s: int(c) for s, c in ord_rows}
    orders_by_status = [
        CounterItem(label=ORD_STATUS_LABELS[s], value=ord_counts.get(s, 0))
        for s in OrderStatus
    ]

    # Выручка за 30 дней (доставленные заказы)
    since = datetime.now(timezone.utc) - timedelta(days=30)
    revenue = (
        await db.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0))
            .where(Order.status == OrderStatus.DELIVERED)
            .where(Order.delivered_at >= since)
        )
    ).scalar_one()

    # Конверсия КП: принятые / отправленные+
    accepted = cp_counts.get(CPStatus.ACCEPTED, 0)
    sent_total = (
        cp_counts.get(CPStatus.SENT, 0)
        + cp_counts.get(CPStatus.ACCEPTED, 0)
        + cp_counts.get(CPStatus.REJECTED, 0)
        + cp_counts.get(CPStatus.EXPIRED, 0)
    )
    conversion = (accepted / sent_total * 100) if sent_total > 0 else 0.0

    # Счётчики пользователей
    total_clients = int(
        (
            await db.execute(
                select(func.count()).select_from(User).where(User.role == UserRole.CLIENT)
            )
        ).scalar_one()
    )
    total_managers = int(
        (
            await db.execute(
                select(func.count()).select_from(User).where(User.role == UserRole.MANAGER)
            )
        ).scalar_one()
    )

    return DashboardSummary(
        requests_by_status=requests_by_status,
        proposals_by_status=proposals_by_status,
        orders_by_status=orders_by_status,
        revenue_30d=Decimal(revenue or 0),
        cp_conversion=round(conversion, 1),
        total_clients=total_clients,
        total_managers=total_managers,
    )
