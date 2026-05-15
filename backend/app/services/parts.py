"""Сервис управления запчастями + история цен."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Part, PriceHistory
from app.schemas.part import PartCreate, PartUpdate


async def list_parts(
    db: AsyncSession,
    *,
    category_id: UUID | None = None,
    search: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    in_stock: bool | None = None,
    is_active: bool | None = True,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Part], int]:
    base = select(Part)
    if category_id is not None:
        base = base.where(Part.category_id == category_id)
    if search:
        like = f"%{search.lower()}%"
        base = base.where(
            func.lower(Part.article).like(like)
            | func.lower(Part.name).like(like)
            | func.lower(func.coalesce(Part.manufacturer, "")).like(like)
        )
    if price_min is not None:
        base = base.where(Part.price >= price_min)
    if price_max is not None:
        base = base.where(Part.price <= price_max)
    if in_stock is True:
        base = base.where(Part.stock_quantity > 0)
    if is_active is not None:
        base = base.where(Part.is_active == is_active)

    total = int(
        (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    )
    rows = (
        await db.execute(
            base.order_by(Part.name).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def get_part(db: AsyncSession, part_id: UUID) -> Part | None:
    return (await db.execute(select(Part).where(Part.id == part_id))).scalar_one_or_none()


async def get_by_article(db: AsyncSession, article: str) -> Part | None:
    return (
        await db.execute(select(Part).where(Part.article == article))
    ).scalar_one_or_none()


async def create_part(
    db: AsyncSession, payload: PartCreate, *, created_by: UUID | None = None
) -> Part:
    part = Part(
        article=payload.article,
        name=payload.name,
        description=payload.description,
        manufacturer=payload.manufacturer,
        category_id=payload.category_id,
        price=payload.price,
        stock_quantity=payload.stock_quantity,
        unit=payload.unit,
        is_active=True,
    )
    db.add(part)
    await db.flush()

    # Запись стартовой цены в историю
    db.add(
        PriceHistory(
            part_id=part.id,
            old_price=None,
            new_price=payload.price,
            changed_by=created_by,
        )
    )
    await db.flush()
    return part


async def update_part(
    db: AsyncSession, part: Part, payload: PartUpdate, *, changed_by: UUID | None = None
) -> tuple[Part, bool]:
    """Возвращает (part, price_changed)."""
    data = payload.model_dump(exclude_unset=True)
    price_changed = False
    old_price = part.price

    if "price" in data and data["price"] != old_price:
        price_changed = True

    for field, value in data.items():
        setattr(part, field, value)
    await db.flush()

    if price_changed:
        db.add(
            PriceHistory(
                part_id=part.id,
                old_price=old_price,
                new_price=part.price,
                changed_by=changed_by,
            )
        )
        await db.flush()

    return part, price_changed


async def set_active(db: AsyncSession, part: Part, is_active: bool) -> Part:
    part.is_active = is_active
    await db.flush()
    return part


async def list_price_history(db: AsyncSession, part_id: UUID) -> list[PriceHistory]:
    rows = (
        await db.execute(
            select(PriceHistory)
            .where(PriceHistory.part_id == part_id)
            .order_by(PriceHistory.changed_at.desc())
        )
    ).scalars().all()
    return list(rows)
