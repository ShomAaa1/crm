"""Схемы для запчастей."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PartBase(BaseModel):
    article: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    manufacturer: str | None = Field(default=None, max_length=255)
    category_id: UUID | None = None
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0)
    unit: str = Field(default="шт", min_length=1, max_length=20)


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    article: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    manufacturer: str | None = Field(default=None, max_length=255)
    category_id: UUID | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stock_quantity: int | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=20)


class PartOut(BaseModel):
    id: UUID
    article: str
    name: str
    description: str | None = None
    manufacturer: str | None = None
    category_id: UUID | None = None
    price: Decimal
    stock_quantity: int
    unit: str
    is_active: bool

    class Config:
        from_attributes = True


class PriceHistoryEntry(BaseModel):
    id: UUID
    old_price: Decimal | None = None
    new_price: Decimal
    changed_by: UUID | None = None
    changed_at: datetime

    class Config:
        from_attributes = True
