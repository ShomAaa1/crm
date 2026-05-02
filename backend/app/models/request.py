from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import RequestStatus, pg_enum


class Request(Base, TimestampMixin):
    __tablename__ = "requests"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    request_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    manager_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("managers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[RequestStatus] = mapped_column(
        pg_enum(RequestStatus, "request_status"),
        default=RequestStatus.NEW,
        server_default=RequestStatus.NEW.value,
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["RequestItem"]] = relationship(
        "RequestItem", back_populates="request", cascade="all, delete-orphan"
    )


class RequestItem(Base):
    __tablename__ = "request_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_request_item_quantity_positive"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    request_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    part_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parts.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    request: Mapped["Request"] = relationship("Request", back_populates="items")
