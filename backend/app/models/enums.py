from enum import StrEnum

from sqlalchemy import Enum as SQLEnum


def pg_enum(enum_cls: type[StrEnum], name: str) -> SQLEnum:
    """Native PG enum that uses StrEnum .value (lowercase) as DB values."""
    return SQLEnum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda cls: [e.value for e in cls],
    )


class UserRole(StrEnum):
    CLIENT = "client"
    MANAGER = "manager"
    HEAD = "head"
    ADMIN = "admin"


class RequestStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    CP_SENT = "cp_sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISION_NEEDED = "revision_needed"
    CLOSED_SUCCESS = "closed_success"
    CLOSED_FAIL = "closed_fail"


class CPStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderStatus(StrEnum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(StrEnum):
    INFO = "info"
    WARNING = "warning"
    TASK = "task"
    SYSTEM = "system"
