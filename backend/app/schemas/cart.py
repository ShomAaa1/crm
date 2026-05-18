"""Схемы корзины клиента."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CartItemIn(BaseModel):
    part_id: UUID
    quantity: int = Field(ge=1, le=10000)


class CartItemQuantityIn(BaseModel):
    quantity: int = Field(ge=1, le=10000)


class CartItemOut(BaseModel):
    id: UUID
    part_id: UUID
    article: str
    name: str
    manufacturer: str | None = None
    unit: str
    price: Decimal
    quantity: int
    line_total: Decimal
    in_stock: bool
    stock_quantity: int


class CartSummary(BaseModel):
    items: list[CartItemOut]
    items_count: int
    total: Decimal
