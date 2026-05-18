"""Сервис корзины клиента.

Корзина живёт в БД — даже если клиент закрыл вкладку, при возврате он
видит сохранённые позиции. Корзина очищается при оформлении заявки.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import CartItem, Part
from app.schemas.cart import CartItemOut, CartSummary


async def get_cart_items(db: AsyncSession, client_id: UUID) -> list[CartItem]:
    rows = (
        await db.execute(
            select(CartItem)
            .options(joinedload(CartItem.part) if hasattr(CartItem, "part") else select(CartItem))
            .where(CartItem.client_id == client_id)
        )
    ).scalars().all()
    return list(rows)


async def _items_with_parts(
    db: AsyncSession, client_id: UUID
) -> list[tuple[CartItem, Part]]:
    """Возвращает пары (item, part). Чистый запрос без relationship."""
    rows = (
        await db.execute(
            select(CartItem, Part)
            .join(Part, Part.id == CartItem.part_id)
            .where(CartItem.client_id == client_id)
            .order_by(Part.name)
        )
    ).all()
    return [(ci, p) for ci, p in rows]


async def build_summary(db: AsyncSession, client_id: UUID) -> CartSummary:
    rows = await _items_with_parts(db, client_id)
    items: list[CartItemOut] = []
    total = Decimal("0.00")
    for ci, p in rows:
        line_total = Decimal(p.price) * ci.quantity
        items.append(
            CartItemOut(
                id=ci.id,
                part_id=p.id,
                article=p.article,
                name=p.name,
                manufacturer=p.manufacturer,
                unit=p.unit,
                price=p.price,
                quantity=ci.quantity,
                line_total=line_total,
                in_stock=p.stock_quantity > 0,
                stock_quantity=p.stock_quantity,
            )
        )
        total += line_total
    return CartSummary(items=items, items_count=len(items), total=total)


async def get_item(
    db: AsyncSession, client_id: UUID, part_id: UUID
) -> CartItem | None:
    return (
        await db.execute(
            select(CartItem)
            .where(CartItem.client_id == client_id)
            .where(CartItem.part_id == part_id)
        )
    ).scalar_one_or_none()


async def add_or_increment(
    db: AsyncSession, client_id: UUID, part_id: UUID, quantity: int
) -> CartItem:
    existing = await get_item(db, client_id, part_id)
    if existing is not None:
        existing.quantity += quantity
        await db.flush()
        return existing

    item = CartItem(client_id=client_id, part_id=part_id, quantity=quantity)
    db.add(item)
    await db.flush()
    return item


async def set_quantity(
    db: AsyncSession, item: CartItem, quantity: int
) -> CartItem:
    item.quantity = quantity
    await db.flush()
    return item


async def remove_item(db: AsyncSession, item: CartItem) -> None:
    await db.delete(item)
    await db.flush()


async def clear_cart(db: AsyncSession, client_id: UUID) -> int:
    result = await db.execute(
        delete(CartItem).where(CartItem.client_id == client_id)
    )
    await db.flush()
    return result.rowcount or 0
