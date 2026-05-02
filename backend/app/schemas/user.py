"""Схемы для CRUD пользователей (admin only)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserRole
from app.utils.validators import is_strong_password


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if not is_strong_password(v):
            raise ValueError("пароль должен содержать минимум 8 символов, букву и цифру")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not is_strong_password(v):
            raise ValueError("пароль должен содержать минимум 8 символов, букву и цифру")
        return v


class UserListItem(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    full_name: str
    phone: str | None = None
    is_active: bool

    class Config:
        from_attributes = True
