"""Эндпоинты экспорта данных в Excel (ФТ-09-04)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models import (
    Client,
    CommercialProposal,
    Manager,
    Order,
    Request,
    User,
)
from app.models.enums import UserRole
from app.services.excel import render_xlsx

router = APIRouter(prefix="/exports", tags=["exports"])

head_or_admin = require_role(UserRole.HEAD, UserRole.ADMIN)


def _xlsx_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/requests.xlsx")
async def export_requests(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(head_or_admin),
) -> Response:
    rows = (
        await db.execute(
            select(
                Request.request_number,
                Request.status,
                Client.company_name,
                Client.inn,
                User.full_name.label("mgr"),
                Request.created_at,
                Request.taken_at,
                Request.closed_at,
            )
            .join(Client, Client.id == Request.client_id)
            .outerjoin(Manager, Manager.id == Request.manager_id)
            .outerjoin(User, User.id == Manager.user_id)
            .order_by(Request.created_at.desc())
        )
    ).all()

    data = []
    for r in rows:
        data.append(
            [
                r.request_number,
                r.status.value,
                r.company_name,
                r.inn,
                r.mgr or "—",
                r.created_at.replace(tzinfo=None) if r.created_at else None,
                r.taken_at.replace(tzinfo=None) if r.taken_at else None,
                r.closed_at.replace(tzinfo=None) if r.closed_at else None,
            ]
        )

    xlsx = render_xlsx(
        sheet_title="Заявки",
        headers=[
            "№ заявки",
            "Статус",
            "Клиент",
            "ИНН",
            "Менеджер",
            "Создана",
            "Взята в работу",
            "Закрыта",
        ],
        rows=data,
        column_widths=[20, 18, 32, 14, 26, 19, 19, 19],
    )
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    return _xlsx_response(xlsx, f"requests_{stamp}.xlsx")


@router.get("/proposals.xlsx")
async def export_proposals(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(head_or_admin),
) -> Response:
    rows = (
        await db.execute(
            select(
                CommercialProposal.cp_number,
                CommercialProposal.status,
                CommercialProposal.version,
                CommercialProposal.total_amount,
                CommercialProposal.created_at,
                CommercialProposal.sent_at,
                CommercialProposal.valid_until,
                Request.request_number,
                Client.company_name,
                User.full_name.label("mgr"),
            )
            .outerjoin(Request, Request.id == CommercialProposal.request_id)
            .outerjoin(Client, Client.id == Request.client_id)
            .outerjoin(Manager, Manager.id == CommercialProposal.manager_id)
            .outerjoin(User, User.id == Manager.user_id)
            .order_by(CommercialProposal.created_at.desc())
        )
    ).all()

    data = []
    for r in rows:
        data.append(
            [
                r.cp_number,
                r.status.value,
                r.version,
                float(r.total_amount) if r.total_amount else 0,
                r.request_number,
                r.company_name,
                r.mgr or "—",
                r.created_at.replace(tzinfo=None) if r.created_at else None,
                r.sent_at.replace(tzinfo=None) if r.sent_at else None,
                r.valid_until,
            ]
        )
    xlsx = render_xlsx(
        sheet_title="Коммерческие предложения",
        headers=[
            "№ КП",
            "Статус",
            "Версия",
            "Сумма, ₽",
            "По заявке",
            "Клиент",
            "Менеджер",
            "Создано",
            "Отправлено",
            "Действительно до",
        ],
        rows=data,
        column_widths=[18, 18, 8, 14, 18, 32, 26, 19, 19, 19],
    )
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    return _xlsx_response(xlsx, f"proposals_{stamp}.xlsx")


@router.get("/orders.xlsx")
async def export_orders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(head_or_admin),
) -> Response:
    rows = (
        await db.execute(
            select(
                Order.order_number,
                Order.status,
                Order.total_amount,
                Order.created_at,
                Order.delivered_at,
                Client.company_name,
                Client.inn,
                User.full_name.label("mgr"),
            )
            .outerjoin(Client, Client.id == Order.client_id)
            .outerjoin(Manager, Manager.id == Order.manager_id)
            .outerjoin(User, User.id == Manager.user_id)
            .order_by(Order.created_at.desc())
        )
    ).all()

    data = []
    for r in rows:
        data.append(
            [
                r.order_number,
                r.status.value,
                float(r.total_amount) if r.total_amount else 0,
                r.company_name or "—",
                r.inn or "—",
                r.mgr or "—",
                r.created_at.replace(tzinfo=None) if r.created_at else None,
                r.delivered_at.replace(tzinfo=None) if r.delivered_at else None,
            ]
        )
    xlsx = render_xlsx(
        sheet_title="Заказы",
        headers=[
            "№ заказа",
            "Статус",
            "Сумма, ₽",
            "Клиент",
            "ИНН",
            "Менеджер",
            "Создан",
            "Доставлен",
        ],
        rows=data,
        column_widths=[20, 16, 14, 32, 14, 26, 19, 19],
    )
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    return _xlsx_response(xlsx, f"orders_{stamp}.xlsx")
