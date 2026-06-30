"""Схемы коммерческих предложений (КП)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import CPStatus


class CPItemUpdate(BaseModel):
    """Обновление позиции КП (по cp_item.id)."""

    id: UUID
    quantity: int = Field(ge=1, le=10000)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    discount_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2
    )


class CPItemAdd(BaseModel):
    """Добавление новой позиции в черновик КП (ФТ-11)."""

    part_id: UUID
    quantity: int = Field(ge=1, le=10000)
    unit_price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    discount_percent: Decimal = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2
    )


class CPDraftUpdate(BaseModel):
    """Редактирование черновика КП: позиции + условия."""

    items: list[CPItemUpdate] | None = None
    items_to_remove: list[UUID] | None = None
    items_to_add: list[CPItemAdd] | None = None
    payment_terms: str | None = Field(default=None, max_length=2000)
    delivery_terms: str | None = Field(default=None, max_length=2000)
    valid_until: date | None = None


class CPItemOut(BaseModel):
    id: UUID
    part_id: UUID | None = None
    article: str | None = None
    name: str
    quantity: int
    unit_price: Decimal
    discount_percent: Decimal
    total_price: Decimal


class CPListItem(BaseModel):
    id: UUID
    cp_number: str
    request_id: UUID
    request_number: str | None = None
    client_company: str | None = None
    manager_id: UUID
    manager_name: str | None = None
    status: CPStatus
    valid_until: date | None = None
    total_amount: Decimal | None = None
    version: int
    created_at: datetime
    sent_at: datetime | None = None


class CPDetail(CPListItem):
    payment_terms: str | None = None
    delivery_terms: str | None = None
    items: list[CPItemOut]


class CPRejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
