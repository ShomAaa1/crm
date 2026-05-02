"""CRUD пользователей — только для роли admin."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.middleware.problem import ProblemException
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserListItem, UserUpdate
from app.services import users as users_service
from app.services.audit import log_action
from app.services.auth import revoke_all_user_refreshes

router = APIRouter(prefix="/users", tags=["users"])

admin_only = require_role(UserRole.ADMIN)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=Page[UserListItem])
async def list_users(
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
) -> Page[UserListItem]:
    items, total = await users_service.list_users(
        db, role=role, is_active=is_active, search=search, limit=limit, offset=offset
    )
    return Page[UserListItem](
        items=[UserListItem.model_validate(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=UserListItem, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(admin_only),
) -> UserListItem:
    if await users_service.get_by_email(db, payload.email):
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail="Пользователь с таким email уже существует",
        )

    user = await users_service.create_user(db, payload)
    await log_action(
        db,
        user_id=actor.id,
        action="user.create",
        entity_type="user",
        entity_id=user.id,
        details={"email": user.email, "role": user.role.value},
        ip_address=_client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return UserListItem.model_validate(user)


@router.get("/{user_id}", response_model=UserListItem)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(admin_only),
) -> UserListItem:
    user = await users_service.get_user(db, user_id)
    if user is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Пользователь не найден",
        )
    return UserListItem.model_validate(user)


@router.patch("/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(admin_only),
) -> UserListItem:
    user = await users_service.get_user(db, user_id)
    if user is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Пользователь не найден",
        )

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="Нет полей для обновления",
        )

    password_changed = "password" in changes
    role_changed = "role" in changes and changes["role"] != user.role
    deactivated = changes.get("is_active") is False and user.is_active

    user = await users_service.update_user(db, user, payload)

    audit_details = {
        k: (v.value if hasattr(v, "value") else v)
        for k, v in changes.items()
        if k != "password"
    }
    if password_changed:
        audit_details["password_changed"] = True
    await log_action(
        db,
        user_id=actor.id,
        action="user.update",
        entity_type="user",
        entity_id=user.id,
        details=audit_details,
        ip_address=_client_ip(request),
    )

    if password_changed or role_changed or deactivated:
        await revoke_all_user_refreshes(user.id)

    await db.commit()
    await db.refresh(user)
    return UserListItem.model_validate(user)


@router.post("/{user_id}/block", status_code=status.HTTP_204_NO_CONTENT)
async def block_user(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(admin_only),
) -> Response:
    user = await users_service.get_user(db, user_id)
    if user is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Пользователь не найден",
        )
    if user.id == actor.id:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="Нельзя заблокировать самого себя",
        )

    if user.is_active:
        await users_service.set_active(db, user, False)
        await log_action(
            db,
            user_id=actor.id,
            action="user.block",
            entity_type="user",
            entity_id=user.id,
            ip_address=_client_ip(request),
        )
        await revoke_all_user_refreshes(user.id)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/unblock", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(admin_only),
) -> Response:
    user = await users_service.get_user(db, user_id)
    if user is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Пользователь не найден",
        )

    if not user.is_active:
        await users_service.set_active(db, user, True)
        await log_action(
            db,
            user_id=actor.id,
            action="user.unblock",
            entity_type="user",
            entity_id=user.id,
            ip_address=_client_ip(request),
        )
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
