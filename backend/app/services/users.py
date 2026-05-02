"""Сервис управления пользователями (admin only).

Только сама сущность User: запись в clients/managers создаётся отдельными
эндпоинтами в соответствующих модулях.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.enums import UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import hash_password


async def list_users(
    db: AsyncSession,
    *,
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[User], int]:
    base = select(User)
    if role is not None:
        base = base.where(User.role == role)
    if is_active is not None:
        base = base.where(User.is_active == is_active)
    if search:
        like = f"%{search.lower()}%"
        base = base.where(
            func.lower(User.email).like(like) | func.lower(User.full_name).like(like)
        )

    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar_one()

    rows = (
        await db.execute(base.order_by(User.created_at.desc()).limit(limit).offset(offset))
    ).scalars().all()
    return list(rows), int(total)


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
        phone=payload.phone,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def update_user(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(user, field, value)
    await db.flush()
    return user


async def set_active(db: AsyncSession, user: User, is_active: bool) -> User:
    user.is_active = is_active
    await db.flush()
    return user
