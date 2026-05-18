"""Сервис заявок (requests).

Жизненный цикл статусов (этап 3 реализует подмножество):

  new ──► in_progress ──► cp_sent ──► accepted ──► closed_success
   │           │               │             │
   │           │               └► rejected ──┴► closed_fail
   │           │
   │           └► revision_needed ──► in_progress (цикл)
   │
   └► cancelled (только из new)

На этапе 3 переходов меньше — статусы, связанные с КП, появятся в этапе 4.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, Manager, Part, Request, RequestItem, User
from app.models.enums import RequestStatus, UserRole
from app.services import cart as cart_svc

SLA_HOURS_FOR_NEW = 24


# --- Допустимые переходы статусов ---------------------------------------

ALLOWED_TRANSITIONS: dict[RequestStatus, set[RequestStatus]] = {
    RequestStatus.NEW: {RequestStatus.IN_PROGRESS, RequestStatus.CANCELLED},
    RequestStatus.IN_PROGRESS: {
        RequestStatus.CP_SENT,
        RequestStatus.REVISION_NEEDED,
        RequestStatus.CLOSED_FAIL,
    },
    RequestStatus.CP_SENT: {
        RequestStatus.ACCEPTED,
        RequestStatus.REJECTED,
        RequestStatus.REVISION_NEEDED,
    },
    RequestStatus.ACCEPTED: {RequestStatus.CLOSED_SUCCESS},
    RequestStatus.REJECTED: {RequestStatus.CLOSED_FAIL},
    RequestStatus.REVISION_NEEDED: {RequestStatus.IN_PROGRESS, RequestStatus.CLOSED_FAIL},
    RequestStatus.CLOSED_SUCCESS: set(),
    RequestStatus.CLOSED_FAIL: set(),
    RequestStatus.CANCELLED: set(),
}


def can_transition(from_status: RequestStatus, to_status: RequestStatus) -> bool:
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


# --- Создание номера заявки --------------------------------------------

async def _next_request_number(db: AsyncSession) -> str:
    """Генерирует номер вида REQ-YYYYMMDD-NNNN."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"REQ-{today}-"
    q = select(func.count()).select_from(Request).where(Request.request_number.like(f"{prefix}%"))
    n = int((await db.execute(q)).scalar_one()) + 1
    return f"{prefix}{n:04d}"


# --- Создание заявки из корзины -----------------------------------------

async def create_from_cart(
    db: AsyncSession, client: Client, comment: str | None
) -> Request:
    pairs = await cart_svc._items_with_parts(db, client.id)
    if not pairs:
        raise ValueError("Корзина пуста")

    number = await _next_request_number(db)
    sla = datetime.now(timezone.utc) + timedelta(hours=SLA_HOURS_FOR_NEW)

    request = Request(
        request_number=number,
        client_id=client.id,
        manager_id=client.assigned_manager_id,
        status=RequestStatus.NEW,
        comment=comment,
        sla_deadline=sla,
    )
    db.add(request)
    await db.flush()

    for ci, part in pairs:
        db.add(
            RequestItem(
                request_id=request.id,
                part_id=part.id,
                description=f"{part.article} — {part.name}",
                quantity=ci.quantity,
                price_at_moment=part.price,
            )
        )

    await cart_svc.clear_cart(db, client.id)
    await db.flush()
    return request


# --- Список заявок с агрегатами ----------------------------------------

async def list_for_user(
    db: AsyncSession,
    user: User,
    *,
    status: RequestStatus | None = None,
    only_unassigned: bool = False,
    only_mine: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Возвращает (rows, total). Каждая строка — dict с агрегатами."""
    q = (
        select(
            Request,
            Client.company_name,
            User.full_name.label("manager_name"),
            func.count(RequestItem.id).label("items_count"),
            func.coalesce(
                func.sum(RequestItem.price_at_moment * RequestItem.quantity),
                0,
            ).label("total"),
        )
        .join(Client, Client.id == Request.client_id)
        .outerjoin(Manager, Manager.id == Request.manager_id)
        .outerjoin(User, User.id == Manager.user_id)
        .outerjoin(RequestItem, RequestItem.request_id == Request.id)
        .group_by(Request.id, Client.company_name, User.full_name)
    )

    if user.role == UserRole.CLIENT:
        client_id_q = select(Client.id).where(Client.user_id == user.id).scalar_subquery()
        q = q.where(Request.client_id == client_id_q)
    elif user.role == UserRole.MANAGER:
        manager_id_q = (
            select(Manager.id).where(Manager.user_id == user.id).scalar_subquery()
        )
        if only_unassigned:
            q = q.where(Request.manager_id.is_(None))
        elif only_mine:
            q = q.where(Request.manager_id == manager_id_q)
        else:
            from sqlalchemy import or_

            q = q.where(
                or_(
                    Request.manager_id == manager_id_q,
                    Request.manager_id.is_(None),
                )
            )
    # head/admin — без ограничений

    if status is not None:
        q = q.where(Request.status == status)

    # total count (берём DISTINCT по Request.id из подзапроса)
    count_q = select(func.count()).select_from(q.subquery())
    total = int((await db.execute(count_q)).scalar_one())

    q = q.order_by(Request.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).all()
    now = datetime.now(timezone.utc)

    items: list[dict] = []
    for r, company, mgr_name, items_count, total_sum in rows:
        sla_overdue = bool(
            r.sla_deadline
            and r.status in (RequestStatus.NEW, RequestStatus.IN_PROGRESS)
            and r.sla_deadline < now
        )
        items.append(
            {
                "request": r,
                "client_company": company,
                "manager_name": mgr_name,
                "items_count": int(items_count or 0),
                "total": Decimal(total_sum or 0),
                "sla_overdue": sla_overdue,
            }
        )
    return items, total


async def get_request(db: AsyncSession, request_id: UUID) -> Request | None:
    return (
        await db.execute(select(Request).where(Request.id == request_id))
    ).scalar_one_or_none()


async def load_items_with_parts(
    db: AsyncSession, request_id: UUID
) -> list[tuple[RequestItem, Part | None]]:
    rows = (
        await db.execute(
            select(RequestItem, Part)
            .outerjoin(Part, Part.id == RequestItem.part_id)
            .where(RequestItem.request_id == request_id)
            .order_by(RequestItem.id)
        )
    ).all()
    return [(ri, p) for ri, p in rows]


# --- Доступ к заявке ----------------------------------------------------

async def can_access(db: AsyncSession, user: User, request: Request) -> bool:
    if user.role in (UserRole.HEAD, UserRole.ADMIN):
        return True
    if user.role == UserRole.CLIENT:
        client = (
            await db.execute(select(Client).where(Client.user_id == user.id))
        ).scalar_one_or_none()
        return client is not None and request.client_id == client.id
    if user.role == UserRole.MANAGER:
        manager = (
            await db.execute(select(Manager).where(Manager.user_id == user.id))
        ).scalar_one_or_none()
        if manager is None:
            return False
        return (
            request.manager_id is None or request.manager_id == manager.id
        )
    return False


# --- Действия над заявкой ----------------------------------------------

async def take_to_work(
    db: AsyncSession, request: Request, manager: Manager
) -> Request:
    """new → in_progress, фиксирует manager_id и taken_at."""
    if request.status != RequestStatus.NEW:
        raise ValueError("Заявку можно взять в работу только в статусе 'new'")
    if request.manager_id is not None and request.manager_id != manager.id:
        raise ValueError("Заявка уже назначена другому менеджеру")
    request.status = RequestStatus.IN_PROGRESS
    request.manager_id = manager.id
    request.taken_at = datetime.now(timezone.utc)
    await db.flush()
    return request


async def change_status(
    db: AsyncSession, request: Request, new_status: RequestStatus
) -> Request:
    if not can_transition(request.status, new_status):
        raise ValueError(
            f"Недопустимый переход: {request.status.value} → {new_status.value}"
        )
    request.status = new_status
    if new_status in (
        RequestStatus.CLOSED_SUCCESS,
        RequestStatus.CLOSED_FAIL,
        RequestStatus.CANCELLED,
    ):
        request.closed_at = datetime.now(timezone.utc)
    await db.flush()
    return request


async def cancel_by_client(db: AsyncSession, request: Request) -> Request:
    """Клиент может отменить заявку только если она ещё новая."""
    if request.status != RequestStatus.NEW:
        raise ValueError("Отменить можно только новую заявку")
    return await change_status(db, request, RequestStatus.CANCELLED)
