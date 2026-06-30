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
from app.models.enums import NotificationType, RequestStatus, UserRole
from app.services import cart as cart_svc
from app.services import notifications as notif_svc

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

    # Уведомления: всем менеджерам о новой заявке (для распределения)
    managers = (
        await db.execute(
            select(Manager.user_id).where(Manager.is_available == True)  # noqa: E712
        )
    ).scalars().all()
    for mgr_user_id in managers:
        await notif_svc.create(
            db,
            user_id=mgr_user_id,
            title=f"Новая заявка {request.request_number}",
            message=f"Клиент: {client.company_name}. Сумма: см. детали.",
            n_type=NotificationType.INFO,
            related_entity_type="request",
            related_entity_id=request.id,
        )

    return request


# --- Создание заявки менеджером от имени клиента ------------------------

async def create_for_client(
    db: AsyncSession,
    client: Client,
    manager: Manager,
    items: list[dict],
    comment: str | None,
) -> Request:
    """Оформление заявки менеджером от имени клиента (on behalf of).

    В отличие от create_from_cart позиции передаются явно (список
    {"part_id": UUID, "quantity": int}), корзина клиента не используется.
    Заявка сразу закрепляется за создавшим её менеджером и переводится
    в статус IN_PROGRESS — он же ведёт её дальше.
    """
    if not items:
        raise ValueError("Не указаны позиции заявки")

    part_ids = [it["part_id"] for it in items]
    parts = {
        p.id: p
        for p in (
            await db.execute(select(Part).where(Part.id.in_(part_ids)))
        ).scalars().all()
    }
    missing = [str(pid) for pid in part_ids if pid not in parts]
    if missing:
        raise ValueError(f"Позиции не найдены: {', '.join(missing)}")

    number = await _next_request_number(db)
    now = datetime.now(timezone.utc)

    request = Request(
        request_number=number,
        client_id=client.id,
        manager_id=manager.id,
        status=RequestStatus.IN_PROGRESS,
        comment=comment,
        taken_at=now,
        sla_deadline=now + timedelta(hours=SLA_HOURS_FOR_NEW),
    )
    db.add(request)
    await db.flush()

    for it in items:
        part = parts[it["part_id"]]
        db.add(
            RequestItem(
                request_id=request.id,
                part_id=part.id,
                description=f"{part.article} — {part.name}",
                quantity=it["quantity"],
                price_at_moment=part.price,
            )
        )
    await db.flush()

    # Уведомление клиенту: для него оформлена заявка (прозрачность on-behalf)
    if client.user_id:
        await notif_svc.create(
            db,
            user_id=client.user_id,
            title=f"Для вас оформлена заявка {request.request_number}",
            message="Менеджер оформил заявку от вашего имени.",
            n_type=NotificationType.INFO,
            related_entity_type="request",
            related_entity_id=request.id,
        )

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
    else:
        # head/admin — видят все заявки, но scope-фильтры тоже применяются
        if only_unassigned:
            q = q.where(Request.manager_id.is_(None))
        elif only_mine:
            # «Мои» для head/admin не имеет смысла — у них нет своих заявок
            # как у менеджера. Возвращаем пустой набор, чтобы UI не врал.
            q = q.where(Request.id == None)  # noqa: E711

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

    # Уведомление клиенту: заявка взята в работу
    client = (
        await db.execute(select(Client).where(Client.id == request.client_id))
    ).scalar_one_or_none()
    if client:
        manager_user = (
            await db.execute(select(User).where(User.id == manager.user_id))
        ).scalar_one_or_none()
        await notif_svc.create(
            db,
            user_id=client.user_id,
            title=f"Заявка {request.request_number} взята в работу",
            message=f"Ваш менеджер: {manager_user.full_name if manager_user else ''}",
            n_type=NotificationType.INFO,
            related_entity_type="request",
            related_entity_id=request.id,
        )

    return request


async def assign_manager(
    db: AsyncSession,
    request: Request,
    manager: Manager,
    reason: str | None = None,
) -> Request:
    """UC-11 / ФТ-11-02 — назначение/переназначение менеджера руководителем.

    Допускает назначение в статусах, где заявка ещё не закрыта.
    """
    closed_statuses = (
        RequestStatus.CLOSED_SUCCESS,
        RequestStatus.CLOSED_FAIL,
        RequestStatus.CANCELLED,
    )
    if request.status in closed_statuses:
        raise ValueError("Нельзя назначать менеджера на закрытую заявку")
    if not manager.is_available:
        raise ValueError("Выбранный менеджер недоступен (отпуск/блокировка)")
    if request.manager_id == manager.id:
        raise ValueError("Этот менеджер уже назначен на заявку")

    previous_manager_id = request.manager_id
    request.manager_id = manager.id

    # При первом назначении в статусе NEW сразу переводим в IN_PROGRESS,
    # чтобы заявка перестала висеть в очереди "Без менеджера".
    if request.status == RequestStatus.NEW:
        request.status = RequestStatus.IN_PROGRESS
        if request.taken_at is None:
            request.taken_at = datetime.now(timezone.utc)

    await db.flush()

    # Уведомление новому менеджеру
    suffix = f" Причина: {reason}" if reason else ""
    await notif_svc.create(
        db,
        user_id=manager.user_id,
        title=f"Вам назначена заявка {request.request_number}",
        message=(
            "Руководитель назначил вас ответственным за заявку." + suffix
        ),
        n_type=NotificationType.INFO,
        related_entity_type="request",
        related_entity_id=request.id,
    )

    # Уведомление предыдущему менеджеру (если было переназначение)
    if previous_manager_id and previous_manager_id != manager.id:
        prev_manager = (
            await db.execute(
                select(Manager).where(Manager.id == previous_manager_id)
            )
        ).scalar_one_or_none()
        if prev_manager:
            await notif_svc.create(
                db,
                user_id=prev_manager.user_id,
                title=f"Заявка {request.request_number} переназначена",
                message=(
                    f"Заявка передана другому менеджеру руководителем."
                    + (f" Причина: {reason}" if reason else "")
                ),
                n_type=NotificationType.WARNING,
                related_entity_type="request",
                related_entity_id=request.id,
            )

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
