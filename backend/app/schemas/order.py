"""Схемы заказов."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import OrderStatus


class OrderUpdateIn(BaseModel):
    delivery_address: str | None = Field(default=None, max_length=2000)
    payment_terms: str | None = Field(default=None, max_length=2000)
    tracking_number: str | None = Field(default=None, max_length=100)


class OrderStatusChangeIn(BaseModel):
    status: OrderStatus
    reason: str | None = Field(default=None, max_length=500)


class OrderItemOut(BaseModel):
    id: UUID
    part_id: UUID
    article: str | None = None
    name: str | None = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class OrderListItem(BaseModel):
    id: UUID
    order_number: str
    status: OrderStatus
    client_id: UUID
    client_company: str | None = None
    manager_id: UUID | None = None
    manager_name: str | None = None
    cp_id: UUID | None = None
    cp_number: str | None = None
    items_count: int
    total_amount: Decimal
    delivery_address: str | None = None
    tracking_number: str | None = None
    created_at: datetime
    delivered_at: datetime | None = None


class OrderDetail(OrderListItem):
    payment_terms: str | None = None
    items: list[OrderItemOut]
