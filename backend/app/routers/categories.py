"""Эндпоинты управления категориями каталога."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.middleware.problem import ProblemException
from app.models import User
from app.models.enums import UserRole
from app.schemas.category import (
    CategoryCreate,
    CategoryOut,
    CategoryTreeNode,
    CategoryUpdate,
)
from app.services import categories as svc
from app.services.audit import log_action

router = APIRouter(prefix="/categories", tags=["catalog"])

manager_or_admin = require_role(UserRole.MANAGER, UserRole.HEAD, UserRole.ADMIN)
admin_only = require_role(UserRole.ADMIN)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CategoryOut]:
    rows = await svc.list_categories(db)
    return [CategoryOut.model_validate(c) for c in rows]


@router.get("/tree", response_model=list[CategoryTreeNode])
async def category_tree(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CategoryTreeNode]:
    return await svc.build_tree(db)


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CategoryOut:
    category = await svc.get_category(db, category_id)
    if category is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Категория не найдена",
        )
    return CategoryOut.model_validate(category)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_admin),
) -> CategoryOut:
    if await svc.get_by_slug(db, payload.slug):
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail="Категория с таким slug уже существует",
        )

    if payload.parent_id and not await svc.get_category(db, payload.parent_id):
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="Родительская категория не найдена",
        )

    category = await svc.create_category(db, payload)
    await log_action(
        db,
        user_id=actor.id,
        action="category.create",
        entity_type="category",
        entity_id=category.id,
        details={"name": category.name, "slug": category.slug},
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(category)
    return CategoryOut.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_admin),
) -> CategoryOut:
    category = await svc.get_category(db, category_id)
    if category is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Категория не найдена",
        )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="Нет полей для обновления",
        )

    if "slug" in data and data["slug"] != category.slug:
        if await svc.get_by_slug(db, data["slug"]):
            raise ProblemException(
                status_code=status.HTTP_409_CONFLICT,
                title="Conflict",
                detail="Категория с таким slug уже существует",
            )

    if "parent_id" in data and data["parent_id"]:
        if data["parent_id"] == category_id:
            raise ProblemException(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Bad Request",
                detail="Категория не может быть родителем самой себе",
            )
        if not await svc.get_category(db, data["parent_id"]):
            raise ProblemException(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Bad Request",
                detail="Родительская категория не найдена",
            )

    category = await svc.update_category(db, category, payload)
    await log_action(
        db,
        user_id=actor.id,
        action="category.update",
        entity_type="category",
        entity_id=category.id,
        details=data,
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(category)
    return CategoryOut.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(admin_only),
) -> Response:
    category = await svc.get_category(db, category_id)
    if category is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Категория не найдена",
        )

    if await svc.count_parts_in_category(db, category_id) > 0:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail="В категории есть запчасти — удалить нельзя",
        )

    if await svc.count_children(db, category_id) > 0:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail="У категории есть подкатегории — удалить нельзя",
        )

    await svc.delete_category(db, category)
    await log_action(
        db,
        user_id=actor.id,
        action="category.delete",
        entity_type="category",
        entity_id=category_id,
        details={"name": category.name, "slug": category.slug},
        ip_address=_ip(request),
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
