"""Схемы заявок (requests)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import RequestStatus


class RequestCreate(BaseModel):
    """Создание заявки из текущей корзины клиента."""

    comment: str | None = Field(default=None, max_length=2000)


class RequestItemIn(BaseModel):
    """Позиция заявки при оформлении менеджером от имени клиента."""

    part_id: UUID
    quantity: int = Field(ge=1, le=100000)


class RequestForClientCreate(BaseModel):
    """Оформление заявки менеджером от имени клиента (on behalf of).

    Позиции передаются явно — корзина клиента не используется.
    """

    client_id: UUID
    items: list[RequestItemIn] = Field(min_length=1)
    comment: str | None = Field(default=None, max_length=2000)


class RequestItemOut(BaseModel):
    id: UUID
    part_id: UUID | None = None
    article: str | None = None
    name: str | None = None
    description: str | None = None
    quantity: int
    price_at_moment: Decimal | None = None
    line_total: Decimal | None = None


class RequestListItem(BaseModel):
    id: UUID
    request_number: str
    status: RequestStatus
    client_id: UUID
    client_company: str | None = None
    manager_id: UUID | None = None
    manager_name: str | None = None
    items_count: int
    total: Decimal
    comment: str | None = None
    created_at: datetime
    taken_at: datetime | None = None
    sla_deadline: datetime | None = None
    closed_at: datetime | None = None
    sla_overdue: bool = False


class ClientFinance(BaseModel):
    inn: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    credit_limit: Decimal = Decimal("0")
    debt: Decimal = Decimal("0")
    phone: str | None = None
    email: str | None = None


class RequestDetail(RequestListItem):
    items: list[RequestItemOut]
    client: ClientFinance | None = None


class StatusChangeIn(BaseModel):
    status: RequestStatus
    reason: str | None = Field(default=None, max_length=500)


class AssignManagerIn(BaseModel):
    manager_id: UUID
    reason: str | None = Field(default=None, max_length=500)
