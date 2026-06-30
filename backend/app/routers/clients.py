"""Эндпоинты карточки клиента и истории взаимодействия (БТ-7 / ФТ-14-07)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.middleware.problem import ProblemException
from app.models import (
    Client,
    ClientContact,
    CommercialProposal,
    Manager,
    Order,
    Request,
    User,
)
from app.models.enums import UserRole

router = APIRouter(prefix="/clients", tags=["clients"])

manager_or_above = require_role(UserRole.MANAGER, UserRole.HEAD, UserRole.ADMIN)


class ContactOut(BaseModel):
    id: UUID
    full_name: str
    position: str | None
    phone: str | None
    email: str | None
    is_primary: bool


class ClientCardOut(BaseModel):
    id: UUID
    company_name: str
    inn: str
    kpp: str | None
    ogrn: str | None
    legal_address: str | None
    delivery_address: str | None
    credit_limit: float
    debt: float
    assigned_manager_id: UUID | None
    assigned_manager_name: str | None
    contacts: list[ContactOut]


ActivityKind = Literal[
    "request_created",
    "request_taken",
    "request_status",
    "cp_created",
    "cp_sent",
    "cp_accepted",
    "cp_rejected",
    "order_created",
    "order_status",
]


class ActivityEvent(BaseModel):
    timestamp: datetime
    kind: ActivityKind
    title: str
    description: str | None = None
    entity_type: str
    entity_id: UUID
    entity_number: str | None = None
    actor_name: str | None = None
    amount: float | None = None


async def _check_access(db: AsyncSession, user: User, client: Client) -> None:
    if user.role in (UserRole.HEAD, UserRole.ADMIN):
        return
    if user.role == UserRole.CLIENT:
        if client.user_id != user.id:
            raise ProblemException(
                status_code=403, title="Forbidden", detail="Нет доступа"
            )
        return
    if user.role == UserRole.MANAGER:
        # Менеджер видит карточку только своих клиентов (assigned_manager_id)
        manager = (
            await db.execute(select(Manager).where(Manager.user_id == user.id))
        ).scalar_one_or_none()
        if manager is None:
            raise ProblemException(
                status_code=403, title="Forbidden", detail="Нет доступа"
            )
        if client.assigned_manager_id != manager.id:
            # Менеджер также видит клиента, если он работал с любой его заявкой
            has_any = (
                await db.execute(
                    select(Request.id)
                    .where(Request.client_id == client.id)
                    .where(Request.manager_id == manager.id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if has_any is None:
                raise ProblemException(
                    status_code=403, title="Forbidden", detail="Нет доступа"
                )


class InnCheckOut(BaseModel):
    exists: bool
    client_id: UUID | None = None
    company_name: str | None = None


@router.get("/check-inn", response_model=InnCheckOut)
async def check_inn(
    inn: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> InnCheckOut:
    """Поиск дубля клиента по ИНН (ФТ-14-04).

    Используется UI при создании клиента, чтобы заранее предупредить
    о существующем юр.лице.
    """
    client = (
        await db.execute(select(Client).where(Client.inn == inn))
    ).scalar_one_or_none()
    if client is None:
        return InnCheckOut(exists=False)
    return InnCheckOut(
        exists=True,
        client_id=client.id,
        company_name=client.company_name,
    )


class ClientListItem(BaseModel):
    id: UUID
    company_name: str
    inn: str
    assigned_manager_id: UUID | None = None


@router.get("", response_model=list[ClientListItem])
async def list_clients(
    search: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(manager_or_above),
) -> list[ClientListItem]:
    """Список клиентов для выбора менеджером при оформлении заявки от имени клиента."""
    q = select(Client)
    if search and search.strip():
        like = f"%{search.strip()}%"
        q = q.where(or_(Client.company_name.ilike(like), Client.inn.ilike(like)))
    q = q.order_by(Client.company_name).limit(max(1, min(limit, 200)))
    rows = (await db.execute(q)).scalars().all()
    return [
        ClientListItem(
            id=c.id,
            company_name=c.company_name,
            inn=c.inn,
            assigned_manager_id=c.assigned_manager_id,
        )
        for c in rows
    ]


@router.get("/{client_id}", response_model=ClientCardOut)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClientCardOut:
    client = (
        await db.execute(select(Client).where(Client.id == client_id))
    ).scalar_one_or_none()
    if client is None:
        raise ProblemException(
            status_code=404, title="Not Found", detail="Клиент не найден"
        )
    await _check_access(db, user, client)

    contacts = (
        await db.execute(
            select(ClientContact)
            .where(ClientContact.client_id == client.id)
            .order_by(ClientContact.is_primary.desc(), ClientContact.full_name)
        )
    ).scalars().all()

    assigned_manager_name: str | None = None
    if client.assigned_manager_id:
        assigned_manager_name = (
            await db.execute(
                select(User.full_name)
                .join(Manager, Manager.user_id == User.id)
                .where(Manager.id == client.assigned_manager_id)
            )
        ).scalar_one_or_none()

    # Клиент не должен видеть свои финансы (как и в карточке заявки)
    is_self_view = user.role == UserRole.CLIENT
    return ClientCardOut(
        id=client.id,
        company_name=client.company_name,
        inn=client.inn,
        kpp=client.kpp,
        ogrn=client.ogrn,
        legal_address=client.legal_address,
        delivery_address=client.delivery_address,
        credit_limit=float(client.credit_limit) if not is_self_view else 0.0,
        debt=float(client.debt) if not is_self_view else 0.0,
        assigned_manager_id=client.assigned_manager_id,
        assigned_manager_name=assigned_manager_name,
        contacts=[
            ContactOut(
                id=c.id,
                full_name=c.full_name,
                position=c.position,
                phone=c.phone,
                email=c.email,
                is_primary=c.is_primary,
            )
            for c in contacts
        ],
    )


@router.get("/{client_id}/activity", response_model=list[ActivityEvent])
async def client_activity(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ActivityEvent]:
    """Единая хронология взаимодействия с клиентом (БТ-7 / ФТ-14-07)."""
    client = (
        await db.execute(select(Client).where(Client.id == client_id))
    ).scalar_one_or_none()
    if client is None:
        raise ProblemException(
            status_code=404, title="Not Found", detail="Клиент не найден"
        )
    await _check_access(db, user, client)

    events: list[ActivityEvent] = []

    # === Заявки ===
    requests = (
        await db.execute(
            select(Request, User.full_name)
            .outerjoin(Manager, Manager.id == Request.manager_id)
            .outerjoin(User, User.id == Manager.user_id)
            .where(Request.client_id == client.id)
            .order_by(Request.created_at.desc())
        )
    ).all()

    for r, mgr_name in requests:
        # Создание заявки
        events.append(
            ActivityEvent(
                timestamp=r.created_at,
                kind="request_created",
                title=f"Новая заявка {r.request_number}",
                description=r.comment,
                entity_type="request",
                entity_id=r.id,
                entity_number=r.request_number,
            )
        )
        # Взята в работу
        if r.taken_at:
            events.append(
                ActivityEvent(
                    timestamp=r.taken_at,
                    kind="request_taken",
                    title=f"Заявка {r.request_number} принята в работу",
                    description=None,
                    entity_type="request",
                    entity_id=r.id,
                    entity_number=r.request_number,
                    actor_name=mgr_name,
                )
            )
        # Закрытие
        if r.closed_at:
            events.append(
                ActivityEvent(
                    timestamp=r.closed_at,
                    kind="request_status",
                    title=f"Заявка {r.request_number} закрыта",
                    description=f"Финальный статус: {r.status.value}",
                    entity_type="request",
                    entity_id=r.id,
                    entity_number=r.request_number,
                    actor_name=mgr_name,
                )
            )

    # === КП ===
    request_ids = [r.id for r, _ in requests]
    if request_ids:
        cps = (
            await db.execute(
                select(CommercialProposal, User.full_name)
                .outerjoin(Manager, Manager.id == CommercialProposal.manager_id)
                .outerjoin(User, User.id == Manager.user_id)
                .where(CommercialProposal.request_id.in_(request_ids))
                .order_by(CommercialProposal.created_at.desc())
            )
        ).all()
        for cp, mgr_name in cps:
            events.append(
                ActivityEvent(
                    timestamp=cp.created_at,
                    kind="cp_created",
                    title=f"КП {cp.cp_number} сформировано",
                    description=None,
                    entity_type="cp",
                    entity_id=cp.id,
                    entity_number=cp.cp_number,
                    actor_name=mgr_name,
                    amount=float(cp.total_amount) if cp.total_amount else None,
                )
            )
            if cp.sent_at:
                events.append(
                    ActivityEvent(
                        timestamp=cp.sent_at,
                        kind="cp_sent",
                        title=f"КП {cp.cp_number} отправлено клиенту",
                        description=None,
                        entity_type="cp",
                        entity_id=cp.id,
                        entity_number=cp.cp_number,
                        actor_name=mgr_name,
                        amount=float(cp.total_amount) if cp.total_amount else None,
                    )
                )
            if cp.status.value == "accepted":
                events.append(
                    ActivityEvent(
                        timestamp=cp.updated_at,
                        kind="cp_accepted",
                        title=f"Клиент принял КП {cp.cp_number}",
                        description=None,
                        entity_type="cp",
                        entity_id=cp.id,
                        entity_number=cp.cp_number,
                        amount=float(cp.total_amount) if cp.total_amount else None,
                    )
                )
            elif cp.status.value == "rejected":
                events.append(
                    ActivityEvent(
                        timestamp=cp.updated_at,
                        kind="cp_rejected",
                        title=f"Клиент отклонил КП {cp.cp_number}",
                        description=None,
                        entity_type="cp",
                        entity_id=cp.id,
                        entity_number=cp.cp_number,
                    )
                )

    # === Заказы ===
    orders = (
        await db.execute(
            select(Order)
            .where(Order.client_id == client.id)
            .order_by(Order.created_at.desc())
        )
    ).scalars().all()
    for o in orders:
        events.append(
            ActivityEvent(
                timestamp=o.created_at,
                kind="order_created",
                title=f"Заказ {o.order_number} создан",
                description=None,
                entity_type="order",
                entity_id=o.id,
                entity_number=o.order_number,
                amount=float(o.total_amount) if o.total_amount else None,
            )
        )

    # Сортировка по времени: новые сверху
    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events
