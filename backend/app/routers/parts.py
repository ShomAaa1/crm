"""Эндпоинты управления запчастями."""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.middleware.problem import ProblemException
from app.models import Part, User
from app.models.enums import UserRole
from app.schemas.common import Page
from app.schemas.part import PartCreate, PartOut, PartUpdate, PriceHistoryEntry
from app.services import categories as categories_svc
from app.services import parts as svc
from app.services.audit import log_action

router = APIRouter(prefix="/parts", tags=["catalog"])

manager_or_admin = require_role(UserRole.MANAGER, UserRole.HEAD, UserRole.ADMIN)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=Page[PartOut])
async def list_parts(
    category_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=255),
    price_min: Decimal | None = Query(default=None, ge=0),
    price_max: Decimal | None = Query(default=None, ge=0),
    in_stock: bool | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[PartOut]:
    # Клиенты видят только активные запчасти
    if user.role == UserRole.CLIENT:
        is_active = True

    items, total = await svc.list_parts(
        db,
        category_id=category_id,
        search=search,
        price_min=price_min,
        price_max=price_max,
        in_stock=in_stock,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return Page[PartOut](
        items=[PartOut.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{part_id}", response_model=PartOut)
async def get_part(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PartOut:
    part = await svc.get_part(db, part_id)
    if part is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Запчасть не найдена",
        )
    if not part.is_active and user.role == UserRole.CLIENT:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Запчасть не найдена",
        )
    return PartOut.model_validate(part)


@router.get("/{part_id}/price-history", response_model=list[PriceHistoryEntry])
async def part_price_history(
    part_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(manager_or_admin),
) -> list[PriceHistoryEntry]:
    if not await svc.get_part(db, part_id):
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Запчасть не найдена",
        )
    rows = await svc.list_price_history(db, part_id)
    return [PriceHistoryEntry.model_validate(r) for r in rows]


@router.post("", response_model=PartOut, status_code=status.HTTP_201_CREATED)
async def create_part(
    payload: PartCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_admin),
) -> PartOut:
    if await svc.get_by_article(db, payload.article):
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail="Запчасть с таким артикулом уже существует",
        )
    if payload.category_id and not await categories_svc.get_category(
        db, payload.category_id
    ):
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="Категория не найдена",
        )

    part = await svc.create_part(db, payload, created_by=actor.id)
    await log_action(
        db,
        user_id=actor.id,
        action="part.create",
        entity_type="part",
        entity_id=part.id,
        details={"article": part.article, "name": part.name, "price": str(part.price)},
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(part)
    return PartOut.model_validate(part)


@router.patch("/{part_id}", response_model=PartOut)
async def update_part(
    part_id: UUID,
    payload: PartUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_admin),
) -> PartOut:
    part = await svc.get_part(db, part_id)
    if part is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Запчасть не найдена",
        )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="Нет полей для обновления",
        )

    if "article" in data and data["article"] != part.article:
        if await svc.get_by_article(db, data["article"]):
            raise ProblemException(
                status_code=status.HTTP_409_CONFLICT,
                title="Conflict",
                detail="Запчасть с таким артикулом уже существует",
            )

    if "category_id" in data and data["category_id"]:
        if not await categories_svc.get_category(db, data["category_id"]):
            raise ProblemException(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Bad Request",
                detail="Категория не найдена",
            )

    part, price_changed = await svc.update_part(db, part, payload, changed_by=actor.id)
    audit_details = {k: (str(v) if isinstance(v, Decimal) else v) for k, v in data.items()}
    await log_action(
        db,
        user_id=actor.id,
        action="part.price_change" if price_changed and set(data.keys()) == {"price"}
        else "part.update",
        entity_type="part",
        entity_id=part.id,
        details=audit_details,
        ip_address=_ip(request),
    )
    await db.commit()
    await db.refresh(part)
    return PartOut.model_validate(part)


@router.post("/{part_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_part(
    part_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_admin),
) -> Response:
    part = await svc.get_part(db, part_id)
    if part is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Запчасть не найдена",
        )
    if part.is_active:
        await svc.set_active(db, part, False)
        await log_action(
            db,
            user_id=actor.id,
            action="part.deactivate",
            entity_type="part",
            entity_id=part.id,
            ip_address=_ip(request),
        )
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{part_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_part(
    part_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_admin),
) -> Response:
    part = await svc.get_part(db, part_id)
    if part is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Запчасть не найдена",
        )
    if not part.is_active:
        await svc.set_active(db, part, True)
        await log_action(
            db,
            user_id=actor.id,
            action="part.activate",
            entity_type="part",
            entity_id=part.id,
            ip_address=_ip(request),
        )
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- CSV-импорт прайса ----------------------------------------------------

REQUIRED_COLUMNS = {"article", "name", "price"}


@router.post("/import/csv")
async def import_csv(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_admin),
) -> dict:
    """Импорт прайса из CSV.

    Ожидаемые колонки (UTF-8, разделитель `,` или `;`):
      article, name, price, manufacturer?, category_slug?, stock_quantity?, unit?, description?

    Семантика:
      - если артикул существует — обновляем поля; при смене цены пишем PriceHistory
      - если нет — создаём
      - неполные строки пропускаются с причиной в errors[]
    """
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    # авто-определение разделителя
    try:
        dialect = csv.Sniffer().sniff(raw[:2048], delimiters=";,")
    except csv.Error:
        dialect = csv.get_dialect("excel")
    reader = csv.DictReader(io.StringIO(raw), dialect=dialect)
    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail=f"CSV должен содержать колонки: {', '.join(sorted(REQUIRED_COLUMNS))}",
        )

    created = 0
    updated = 0
    price_changes = 0
    errors: list[dict] = []

    for line_no, row in enumerate(reader, start=2):
        article = (row.get("article") or "").strip()
        name = (row.get("name") or "").strip()
        price_raw = (row.get("price") or "").strip().replace(",", ".")
        if not article or not name or not price_raw:
            errors.append({"line": line_no, "reason": "пустые обязательные поля"})
            continue
        try:
            price = Decimal(price_raw)
            if price < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            errors.append({"line": line_no, "reason": f"некорректная цена '{price_raw}'"})
            continue

        category_id: UUID | None = None
        cat_slug = (row.get("category_slug") or "").strip()
        if cat_slug:
            cat = await categories_svc.get_by_slug(db, cat_slug)
            if cat is None:
                errors.append({"line": line_no, "reason": f"категория '{cat_slug}' не найдена"})
                continue
            category_id = cat.id

        stock_raw = (row.get("stock_quantity") or "0").strip()
        try:
            stock = int(stock_raw) if stock_raw else 0
        except ValueError:
            errors.append({"line": line_no, "reason": f"некорректный остаток '{stock_raw}'"})
            continue

        manufacturer = (row.get("manufacturer") or "").strip() or None
        unit = (row.get("unit") or "шт").strip() or "шт"
        description = (row.get("description") or "").strip() or None

        existing = await svc.get_by_article(db, article)
        if existing is None:
            await svc.create_part(
                db,
                PartCreate(
                    article=article,
                    name=name,
                    description=description,
                    manufacturer=manufacturer,
                    category_id=category_id,
                    price=price,
                    stock_quantity=stock,
                    unit=unit,
                ),
                created_by=actor.id,
            )
            created += 1
        else:
            update_payload = PartUpdate(
                name=name,
                description=description,
                manufacturer=manufacturer,
                category_id=category_id,
                price=price,
                stock_quantity=stock,
                unit=unit,
            )
            _, price_changed = await svc.update_part(
                db, existing, update_payload, changed_by=actor.id
            )
            updated += 1
            if price_changed:
                price_changes += 1

    await log_action(
        db,
        user_id=actor.id,
        action="catalog.import_csv",
        entity_type="part",
        entity_id=None,
        details={
            "created": created,
            "updated": updated,
            "price_changes": price_changes,
            "errors": len(errors),
        },
        ip_address=_ip(request),
    )
    await db.commit()

    return {
        "created": created,
        "updated": updated,
        "price_changes": price_changes,
        "errors": errors,
    }
