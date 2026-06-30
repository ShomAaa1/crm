"""Сервис заказов.

Жизненный цикл:
  created ──► confirmed ──► shipped ──► delivered
       │           │
       └──────► cancelled (можно из created/confirmed)

Создаётся автоматически при accept КП. При переходе created→confirmed
списываем stock_quantity у запчастей. При cancelled (если был confirmed) —
возвращаем на склад.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Client,
    CommercialProposal,
    CPItem,
    Manager,
    Order,
    OrderItem,
    Part,
    User,
)
from app.models.enums import NotificationType, OrderStatus, RequestStatus, UserRole
from app.services import notifications as notif_svc

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def can_transition(from_s: OrderStatus, to_s: OrderStatus) -> bool:
    return to_s in ALLOWED_TRANSITIONS.get(from_s, set())


async def _next_order_number(db: AsyncSession) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"ORD-{today}-"
    q = (
        select(func.count())
        .select_from(Order)
        .where(Order.order_number.like(f"{prefix}%"))
    )
    n = int((await db.execute(q)).scalar_one()) + 1
    return f"{prefix}{n:04d}"


async def create_from_proposal(
    db: AsyncSession, cp: CommercialProposal, client: Client
) -> Order:
    """Создать заказ из принятого КП.

    Адрес доставки — из профиля клиента, payment_terms — из КП.
    """
    existing = (
        await db.execute(select(Order).where(Order.cp_id == cp.id))
    ).scalar_one_or_none()
    if existing is not None:
        return existing  # идемпотентно

    cp_items = (
        await db.execute(select(CPItem).where(CPItem.cp_id == cp.id))
    ).scalars().all()
    if not cp_items:
        raise ValueError("В КП нет позиций")

    number = await _next_order_number(db)
    order = Order(
        order_number=number,
        client_id=client.id,
        manager_id=cp.manager_id,
        cp_id=cp.id,
        status=OrderStatus.CREATED,
        total_amount=cp.total_amount or Decimal("0"),
        delivery_address=client.delivery_address,
        payment_terms=cp.payment_terms
        or "Оплата по счёту в течение 5 рабочих дней после получения товара",
    )
    db.add(order)
    await db.flush()

    for ci in cp_items:
        if ci.part_id is None:
            continue
        db.add(
            OrderItem(
                order_id=order.id,
                part_id=ci.part_id,
                quantity=ci.quantity,
                unit_price=ci.unit_price,
                total_price=ci.total_price,
            )
        )
    await db.flush()
    return order


async def get_order(db: AsyncSession, order_id: UUID) -> Order | None:
    return (
        await db.execute(select(Order).where(Order.id == order_id))
    ).scalar_one_or_none()


async def load_items(
    db: AsyncSession, order_id: UUID
) -> list[tuple[OrderItem, Part | None]]:
    rows = (
        await db.execute(
            select(OrderItem, Part)
            .outerjoin(Part, Part.id == OrderItem.part_id)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.id)
        )
    ).all()
    return [(oi, p) for oi, p in rows]


async def can_access(db: AsyncSession, user: User, order: Order) -> bool:
    if user.role in (UserRole.HEAD, UserRole.ADMIN):
        return True
    if user.role == UserRole.CLIENT:
        client = (
            await db.execute(select(Client).where(Client.user_id == user.id))
        ).scalar_one_or_none()
        return client is not None and order.client_id == client.id
    if user.role == UserRole.MANAGER:
        m = (
            await db.execute(select(Manager).where(Manager.user_id == user.id))
        ).scalar_one_or_none()
        return m is not None and order.manager_id == m.id
    return False


async def update_order(
    db: AsyncSession,
    order: Order,
    *,
    delivery_address: str | None = None,
    payment_terms: str | None = None,
    tracking_number: str | None = None,
) -> Order:
    if delivery_address is not None:
        order.delivery_address = delivery_address
    if payment_terms is not None:
        order.payment_terms = payment_terms
    if tracking_number is not None:
        order.tracking_number = tracking_number
    await db.flush()
    return order


async def change_status(
    db: AsyncSession, order: Order, new_status: OrderStatus
) -> Order:
    if not can_transition(order.status, new_status):
        raise ValueError(
            f"Недопустимый переход: {order.status.value} → {new_status.value}"
        )

    items = await load_items(db, order.id)

    # Списание со склада при confirmed
    if new_status == OrderStatus.CONFIRMED and order.status == OrderStatus.CREATED:
        for oi, part in items:
            if part is None:
                continue
            if part.stock_quantity < oi.quantity:
                raise ValueError(
                    f"Недостаточно на складе: {part.article} (нужно {oi.quantity}, есть {part.stock_quantity})"
                )
        for oi, part in items:
            if part is not None:
                part.stock_quantity -= oi.quantity

    # Возврат на склад при cancelled (если был уже confirmed/shipped)
    if new_status == OrderStatus.CANCELLED and order.status in (
        OrderStatus.CONFIRMED,
        OrderStatus.SHIPPED,
    ):
        for oi, part in items:
            if part is not None:
                part.stock_quantity += oi.quantity

    order.status = new_status

    # Связь с заявкой через КП: при delivered → request.closed_success;
    # при cancelled → request.closed_fail
    if new_status == OrderStatus.DELIVERED:
        order.delivered_at = datetime.now(timezone.utc)
        await _propagate_to_request(db, order, RequestStatus.CLOSED_SUCCESS)
    elif new_status == OrderStatus.CANCELLED:
        await _propagate_to_request(db, order, RequestStatus.CLOSED_FAIL)

    await db.flush()

    # Уведомление клиенту: статус заказа изменился
    client = (
        await db.execute(select(Client).where(Client.id == order.client_id))
    ).scalar_one_or_none()
    if client:
        status_labels = {
            OrderStatus.CONFIRMED: "подтверждён",
            OrderStatus.SHIPPED: "отгружен",
            OrderStatus.DELIVERED: "доставлен",
            OrderStatus.CANCELLED: "отменён",
        }
        label = status_labels.get(new_status, new_status.value)
        await notif_svc.create(
            db,
            user_id=client.user_id,
            title=f"Заказ {order.order_number}: {label}",
            message=(
                f"Трек-номер: {order.tracking_number}"
                if new_status == OrderStatus.SHIPPED and order.tracking_number
                else None
            ),
            n_type=NotificationType.INFO if new_status != OrderStatus.CANCELLED else NotificationType.WARNING,
            related_entity_type="order",
            related_entity_id=order.id,
        )

    return order


async def _propagate_to_request(
    db: AsyncSession, order: Order, target_status: RequestStatus
) -> None:
    """Если у заказа есть КП → находим заявку и закрываем её."""
    if order.cp_id is None:
        return
    cp = (
        await db.execute(
            select(CommercialProposal).where(CommercialProposal.id == order.cp_id)
        )
    ).scalar_one_or_none()
    if cp is None:
        return
    from app.models import Request

    req = (
        await db.execute(select(Request).where(Request.id == cp.request_id))
    ).scalar_one_or_none()
    if req is None:
        return
    if req.status == RequestStatus.ACCEPTED:
        req.status = target_status
        req.closed_at = datetime.now(timezone.utc)


async def list_for_user(
    db: AsyncSession,
    user: User,
    *,
    status: OrderStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    q = (
        select(
            Order,
            Client.company_name,
            User.full_name.label("manager_name"),
            CommercialProposal.cp_number,
            func.count(OrderItem.id).label("items_count"),
        )
        .join(Client, Client.id == Order.client_id)
        .outerjoin(Manager, Manager.id == Order.manager_id)
        .outerjoin(User, User.id == Manager.user_id)
        .outerjoin(CommercialProposal, CommercialProposal.id == Order.cp_id)
        .outerjoin(OrderItem, OrderItem.order_id == Order.id)
        .group_by(Order.id, Client.company_name, User.full_name, CommercialProposal.cp_number)
    )

    if user.role == UserRole.CLIENT:
        client_id_q = select(Client.id).where(Client.user_id == user.id).scalar_subquery()
        q = q.where(Order.client_id == client_id_q)
    elif user.role == UserRole.MANAGER:
        manager_id_q = (
            select(Manager.id).where(Manager.user_id == user.id).scalar_subquery()
        )
        q = q.where(Order.manager_id == manager_id_q)

    if status is not None:
        q = q.where(Order.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = int((await db.execute(count_q)).scalar_one())

    q = q.order_by(Order.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).all()

    return [
        {
            "order": o,
            "client_company": cc,
            "manager_name": mn,
            "cp_number": cpn,
            "items_count": int(ic or 0),
        }
        for o, cc, mn, cpn, ic in rows
    ], total


async def get_order_by_cp(db: AsyncSession, cp_id: UUID) -> Order | None:
    return (
        await db.execute(select(Order).where(Order.cp_id == cp_id))
    ).scalar_one_or_none()
