"""Схемы для категорий каталога."""

from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    parent_id: UUID | None = None

    @field_validator("slug")
    @classmethod
    def _slug_format(cls, v: str) -> str:
        if not SLUG_RE.match(v):
            raise ValueError("slug должен быть в формате lower-case-with-dashes")
        return v


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: UUID | None = None

    @field_validator("slug")
    @classmethod
    def _slug_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not SLUG_RE.match(v):
            raise ValueError("slug должен быть в формате lower-case-with-dashes")
        return v


class CategoryOut(BaseModel):
    id: UUID
    name: str
    slug: str
    parent_id: UUID | None = None

    class Config:
        from_attributes = True


class CategoryTreeNode(CategoryOut):
    children: list["CategoryTreeNode"] = Field(default_factory=list)


CategoryTreeNode.model_rebuild()
