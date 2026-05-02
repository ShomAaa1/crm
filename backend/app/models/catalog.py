from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", backref="children"
    )
    parts: Mapped[list["Part"]] = relationship("Part", back_populates="category")


class Part(Base, TimestampMixin):
    __tablename__ = "parts"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_parts_price_nonneg"),
        CheckConstraint("stock_quantity >= 0", name="ck_parts_stock_nonneg"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    article: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    unit: Mapped[str] = mapped_column(String(20), default="шт", server_default="шт")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    category: Mapped["Category | None"] = relationship("Category", back_populates="parts")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    part_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    new_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    changed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
