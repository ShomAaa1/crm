"""Сервис коммерческих предложений (КП).

Жизненный цикл:
  DRAFT ──► SENT ──► ACCEPTED / REJECTED / EXPIRED

Переходы выполняются менеджером (DRAFT→SENT) и клиентом (SENT→ACCEPTED/REJECTED).
Связь с заявкой:
  - При SEND статус заявки → cp_sent
  - При ACCEPT  статус заявки → accepted
  - При REJECT  статус заявки → rejected
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Client,
    CommercialProposal,
    CPItem,
    Manager,
    Part,
    Request,
    RequestItem,
    User,
)
from app.models.enums import CPStatus, NotificationType, RequestStatus
from app.services import notifications as notif_svc


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def calc_line_total(qty: int, price: Decimal, discount_percent: Decimal) -> Decimal:
    gross = Decimal(qty) * Decimal(price)
    net = gross * (Decimal("100") - Decimal(discount_percent)) / Decimal("100")
    return _round(net)


def calc_total(items: list[CPItem]) -> Decimal:
    return _round(sum((Decimal(i.total_price) for i in items), start=Decimal("0")))


async def _next_cp_number(db: AsyncSession) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"CP-{today}-"
    q = (
        select(func.count())
        .select_from(CommercialProposal)
        .where(CommercialProposal.cp_number.like(f"{prefix}%"))
    )
    n = int((await db.execute(q)).scalar_one()) + 1
    return f"{prefix}{n:04d}"


async def create_draft_from_request(
    db: AsyncSession, request: Request, manager: Manager
) -> CommercialProposal:
    """Создать черновик КП из позиций заявки. На одну заявку — один активный КП."""
    existing = (
        await db.execute(
            select(CommercialProposal).where(CommercialProposal.request_id == request.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("Для этой заявки уже создано КП")

    number = await _next_cp_number(db)
    cp = CommercialProposal(
        cp_number=number,
        request_id=request.id,
        manager_id=manager.id,
        status=CPStatus.DRAFT,
        valid_until=date.today() + timedelta(days=14),
        version=1,
    )
    db.add(cp)
    await db.flush()

    request_items = (
        await db.execute(
            select(RequestItem, Part)
            .outerjoin(Part, Part.id == RequestItem.part_id)
            .where(RequestItem.request_id == request.id)
            .order_by(RequestItem.id)
        )
    ).all()

    total = Decimal("0")
    for ri, part in request_items:
        # Стартовая цена — из price_at_moment (то, что видел клиент при заявке)
        price = Decimal(ri.price_at_moment) if ri.price_at_moment is not None else (
            Decimal(part.price) if part is not None else Decimal("0")
        )
        line_total = calc_line_total(ri.quantity, price, Decimal("0"))
        item = CPItem(
            cp_id=cp.id,
            part_id=ri.part_id,
            name=part.name if part is not None else (ri.description or "Позиция"),
            quantity=ri.quantity,
            unit_price=price,
            discount_percent=Decimal("0"),
            total_price=line_total,
        )
        db.add(item)
        total += line_total

    cp.total_amount = _round(total)
    await db.flush()
    return cp


async def get_proposal(db: AsyncSession, cp_id: UUID) -> CommercialProposal | None:
    return (
        await db.execute(select(CommercialProposal).where(CommercialProposal.id == cp_id))
    ).scalar_one_or_none()


async def get_proposal_by_request(
    db: AsyncSession, request_id: UUID
) -> CommercialProposal | None:
    return (
        await db.execute(
            select(CommercialProposal).where(CommercialProposal.request_id == request_id)
        )
    ).scalar_one_or_none()


async def load_items(db: AsyncSession, cp_id: UUID) -> list[tuple[CPItem, Part | None]]:
    rows = (
        await db.execute(
            select(CPItem, Part)
            .outerjoin(Part, Part.id == CPItem.part_id)
            .where(CPItem.cp_id == cp_id)
            .order_by(CPItem.id)
        )
    ).all()
    return [(ci, p) for ci, p in rows]


async def update_draft(
    db: AsyncSession,
    cp: CommercialProposal,
    *,
    items_updates: list[dict] | None,
    items_to_remove: list[UUID] | None,
    payment_terms: str | None,
    delivery_terms: str | None,
    valid_until: date | None,
) -> CommercialProposal:
    if cp.status != CPStatus.DRAFT:
        raise ValueError("Редактировать можно только черновик КП")

    if items_to_remove:
        for item_id in items_to_remove:
            existing = (
                await db.execute(
                    select(CPItem).where(CPItem.id == item_id).where(CPItem.cp_id == cp.id)
                )
            ).scalar_one_or_none()
            if existing is not None:
                await db.delete(existing)
        await db.flush()

    if items_updates:
        for upd in items_updates:
            item = (
                await db.execute(
                    select(CPItem).where(CPItem.id == upd["id"]).where(CPItem.cp_id == cp.id)
                )
            ).scalar_one_or_none()
            if item is None:
                continue
            item.quantity = upd["quantity"]
            item.unit_price = upd["unit_price"]
            item.discount_percent = upd["discount_percent"]
            item.total_price = calc_line_total(
                upd["quantity"], upd["unit_price"], upd["discount_percent"]
            )
        await db.flush()

    if payment_terms is not None:
        cp.payment_terms = payment_terms
    if delivery_terms is not None:
        cp.delivery_terms = delivery_terms
    if valid_until is not None:
        cp.valid_until = valid_until

    # пересчёт общей суммы
    rows = (await db.execute(select(CPItem).where(CPItem.cp_id == cp.id))).scalars().all()
    cp.total_amount = calc_total(list(rows))
    await db.flush()
    return cp


async def send_proposal(
    db: AsyncSession, cp: CommercialProposal, request: Request
) -> CommercialProposal:
    if cp.status != CPStatus.DRAFT:
        raise ValueError("Отправить можно только черновик")
    cp.status = CPStatus.SENT
    cp.sent_at = datetime.now(timezone.utc)
    request.status = RequestStatus.CP_SENT
    await db.flush()

    # Уведомление клиенту
    client = (
        await db.execute(select(Client).where(Client.id == request.client_id))
    ).scalar_one_or_none()
    if client:
        await notif_svc.create(
            db,
            user_id=client.user_id,
            title=f"Получено коммерческое предложение {cp.cp_number}",
            message=f"По заявке {request.request_number}. Сумма: {cp.total_amount} ₽",
            n_type=NotificationType.INFO,
            related_entity_type="cp",
            related_entity_id=cp.id,
        )
    return cp


async def accept_proposal(
    db: AsyncSession, cp: CommercialProposal, request: Request
) -> CommercialProposal:
    if cp.status != CPStatus.SENT:
        raise ValueError("Принять можно только отправленное КП")
    cp.status = CPStatus.ACCEPTED
    request.status = RequestStatus.ACCEPTED
    await db.flush()

    # Автоматическое создание заказа при принятии КП
    from app.services import orders as orders_svc

    client = (
        await db.execute(select(Client).where(Client.id == request.client_id))
    ).scalar_one_or_none()
    if client is not None:
        try:
            await orders_svc.create_from_proposal(db, cp, client)
        except ValueError:
            # если в КП нет позиций — не падаем, просто не создаём заказ
            pass

    # Уведомление менеджеру: КП принято
    manager = (
        await db.execute(select(Manager).where(Manager.id == cp.manager_id))
    ).scalar_one_or_none()
    if manager:
        await notif_svc.create(
            db,
            user_id=manager.user_id,
            title=f"КП {cp.cp_number} принято клиентом",
            message=f"По заявке {request.request_number}. Создан заказ.",
            n_type=NotificationType.INFO,
            related_entity_type="cp",
            related_entity_id=cp.id,
        )

    return cp


async def reject_proposal(
    db: AsyncSession, cp: CommercialProposal, request: Request
) -> CommercialProposal:
    if cp.status != CPStatus.SENT:
        raise ValueError("Отклонить можно только отправленное КП")
    cp.status = CPStatus.REJECTED
    request.status = RequestStatus.REJECTED
    await db.flush()

    manager = (
        await db.execute(select(Manager).where(Manager.id == cp.manager_id))
    ).scalar_one_or_none()
    if manager:
        await notif_svc.create(
            db,
            user_id=manager.user_id,
            title=f"КП {cp.cp_number} отклонено",
            message=f"По заявке {request.request_number}",
            n_type=NotificationType.WARNING,
            related_entity_type="cp",
            related_entity_id=cp.id,
        )
    return cp


async def revision_request(
    db: AsyncSession, cp: CommercialProposal, request: Request
) -> CommercialProposal:
    """Клиент просит пересчитать КП — возвращаем в черновик, заявка в revision_needed."""
    if cp.status != CPStatus.SENT:
        raise ValueError("Запрос на пересчёт возможен только для отправленного КП")
    cp.status = CPStatus.DRAFT
    cp.version += 1
    cp.sent_at = None
    request.status = RequestStatus.REVISION_NEEDED
    await db.flush()

    manager = (
        await db.execute(select(Manager).where(Manager.id == cp.manager_id))
    ).scalar_one_or_none()
    if manager:
        await notif_svc.create(
            db,
            user_id=manager.user_id,
            title=f"Запрос пересчёта по КП {cp.cp_number}",
            message=f"Клиент попросил пересчитать КП по заявке {request.request_number}",
            n_type=NotificationType.WARNING,
            related_entity_type="cp",
            related_entity_id=cp.id,
        )
    return cp


async def list_for_user(
    db: AsyncSession,
    user: User,
    *,
    status: CPStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    from app.models.enums import UserRole

    q = (
        select(
            CommercialProposal,
            Request.request_number,
            Client.company_name,
            User.full_name.label("manager_name"),
        )
        .join(Request, Request.id == CommercialProposal.request_id)
        .join(Client, Client.id == Request.client_id)
        .join(Manager, Manager.id == CommercialProposal.manager_id)
        .join(User, User.id == Manager.user_id)
    )

    if user.role == UserRole.CLIENT:
        client_id_q = (
            select(Client.id).where(Client.user_id == user.id).scalar_subquery()
        )
        q = q.where(Request.client_id == client_id_q)
        # Клиент видит только отправленные/принятые/отклонённые — не черновики
        q = q.where(CommercialProposal.status != CPStatus.DRAFT)
    elif user.role == UserRole.MANAGER:
        manager_id_q = (
            select(Manager.id).where(Manager.user_id == user.id).scalar_subquery()
        )
        q = q.where(CommercialProposal.manager_id == manager_id_q)
    # head/admin — всё

    if status is not None:
        q = q.where(CommercialProposal.status == status)

    total_q = select(func.count()).select_from(q.subquery())
    total = int((await db.execute(total_q)).scalar_one())

    q = q.order_by(CommercialProposal.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).all()
    return [
        {
            "cp": cp,
            "request_number": rn,
            "client_company": cc,
            "manager_name": mn,
        }
        for cp, rn, cc, mn in rows
    ], total
