"""Схемы задач (UC-10 / ФТ-10-02)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    manager_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority | None = None
    due_date: date | None = None
    status: TaskStatus | None = None


class TaskOut(BaseModel):
    id: UUID
    manager_id: UUID
    manager_name: str | None = None
    assigned_by: UUID | None
    assigned_by_name: str | None = None
    title: str
    description: str | None
    priority: TaskPriority
    status: TaskStatus
    due_date: date | None
    completed_at: datetime | None
    created_at: datetime
    is_overdue: bool = False
