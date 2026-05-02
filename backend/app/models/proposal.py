from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CPStatus, pg_enum


class CommercialProposal(Base, TimestampMixin):
    __tablename__ = "commercial_proposals"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    cp_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    request_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    manager_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("managers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[CPStatus] = mapped_column(
        pg_enum(CPStatus, "cp_status"),
        default=CPStatus.DRAFT,
        server_default=CPStatus.DRAFT.value,
        nullable=False,
    )
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["CPItem"]] = relationship(
        "CPItem", back_populates="proposal", cascade="all, delete-orphan"
    )


class CPItem(Base):
    __tablename__ = "cp_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_cp_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_cp_item_price_nonneg"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    cp_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("commercial_proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    part_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parts.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), server_default="0"
    )
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    proposal: Mapped["CommercialProposal"] = relationship(
        "CommercialProposal", back_populates="items"
    )
