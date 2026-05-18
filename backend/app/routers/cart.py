"""Эндпоинты корзины клиента."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.middleware.problem import ProblemException
from app.models import Client, Part, User
from app.models.enums import UserRole
from app.schemas.cart import CartItemIn, CartItemQuantityIn, CartSummary
from app.services import cart as svc
from app.services.audit import log_action

router = APIRouter(prefix="/cart", tags=["cart"])

client_only = require_role(UserRole.CLIENT)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _get_client_or_403(db: AsyncSession, user: User) -> Client:
    client = (
        await db.execute(select(Client).where(Client.user_id == user.id))
    ).scalar_one_or_none()
    if client is None:
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Пользователь не привязан к клиенту",
        )
    return client


@router.get("", response_model=CartSummary)
async def get_cart(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> CartSummary:
    client = await _get_client_or_403(db, user)
    return await svc.build_summary(db, client.id)


@router.post("/items", response_model=CartSummary, status_code=status.HTTP_201_CREATED)
async def add_item(
    payload: CartItemIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> CartSummary:
    client = await _get_client_or_403(db, user)

    part = (
        await db.execute(select(Part).where(Part.id == payload.part_id))
    ).scalar_one_or_none()
    if part is None or not part.is_active:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Запчасть не найдена или недоступна",
        )

    await svc.add_or_increment(db, client.id, part.id, payload.quantity)
    await log_action(
        db,
        user_id=user.id,
        action="cart.add",
        entity_type="cart_item",
        entity_id=part.id,
        details={"part_id": str(part.id), "quantity": payload.quantity},
        ip_address=_ip(request),
    )
    await db.commit()
    return await svc.build_summary(db, client.id)


@router.patch("/items/{part_id}", response_model=CartSummary)
async def update_item_quantity(
    part_id: UUID,
    payload: CartItemQuantityIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> CartSummary:
    client = await _get_client_or_403(db, user)
    item = await svc.get_item(db, client.id, part_id)
    if item is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Позиция не найдена в корзине",
        )
    await svc.set_quantity(db, item, payload.quantity)
    await log_action(
        db,
        user_id=user.id,
        action="cart.update",
        entity_type="cart_item",
        entity_id=item.id,
        details={"part_id": str(part_id), "quantity": payload.quantity},
        ip_address=_ip(request),
    )
    await db.commit()
    return await svc.build_summary(db, client.id)


@router.delete("/items/{part_id}", response_model=CartSummary)
async def remove_item(
    part_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> CartSummary:
    client = await _get_client_or_403(db, user)
    item = await svc.get_item(db, client.id, part_id)
    if item is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Позиция не найдена в корзине",
        )
    await svc.remove_item(db, item)
    await log_action(
        db,
        user_id=user.id,
        action="cart.remove",
        entity_type="cart_item",
        entity_id=item.id,
        details={"part_id": str(part_id)},
        ip_address=_ip(request),
    )
    await db.commit()
    return await svc.build_summary(db, client.id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> Response:
    client = await _get_client_or_403(db, user)
    removed = await svc.clear_cart(db, client.id)
    if removed > 0:
        await log_action(
            db,
            user_id=user.id,
            action="cart.clear",
            entity_type="cart",
            entity_id=client.id,
            details={"removed": removed},
            ip_address=_ip(request),
        )
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
