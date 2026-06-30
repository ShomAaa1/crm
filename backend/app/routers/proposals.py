"""Эндпоинты коммерческих предложений (КП)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.middleware.problem import ProblemException
from app.models import Client, CommercialProposal, Manager, Part, Request as ReqModel, User
from app.models.enums import CPStatus, UserRole
from app.services.pdf import CPItemData, render_proposal_pdf
from app.schemas.common import Page
from app.schemas.proposal import (
    CPDetail,
    CPDraftUpdate,
    CPItemOut,
    CPListItem,
    CPRejectIn,
)
from app.services import proposals as svc
from app.services import requests as requests_svc
from app.services.audit import log_action

router = APIRouter(prefix="/proposals", tags=["proposals"])

manager_or_above = require_role(UserRole.MANAGER, UserRole.HEAD, UserRole.ADMIN)
client_only = require_role(UserRole.CLIENT)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _build_detail(
    db: AsyncSession, cp_id: UUID
) -> CPDetail:
    cp = await svc.get_proposal(db, cp_id)
    if cp is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="КП не найдено",
        )

    req = await requests_svc.get_request(db, cp.request_id)
    client = (
        await db.execute(select(Client).where(Client.id == req.client_id))
    ).scalar_one_or_none() if req else None

    manager_name = (
        await db.execute(
            select(User.full_name)
            .join(Manager, Manager.user_id == User.id)
            .where(Manager.id == cp.manager_id)
        )
    ).scalar_one_or_none()

    pairs = await svc.load_items(db, cp.id)
    items_out = [
        CPItemOut(
            id=ci.id,
            part_id=ci.part_id,
            article=p.article if p else None,
            name=ci.name,
            quantity=ci.quantity,
            unit_price=ci.unit_price,
            discount_percent=ci.discount_percent,
            total_price=ci.total_price,
        )
        for ci, p in pairs
    ]

    return CPDetail(
        id=cp.id,
        cp_number=cp.cp_number,
        request_id=cp.request_id,
        request_number=req.request_number if req else None,
        client_company=client.company_name if client else None,
        manager_id=cp.manager_id,
        manager_name=manager_name,
        status=cp.status,
        valid_until=cp.valid_until,
        total_amount=cp.total_amount,
        version=cp.version,
        created_at=cp.created_at,
        sent_at=cp.sent_at,
        payment_terms=cp.payment_terms,
        delivery_terms=cp.delivery_terms,
        items=items_out,
    )


async def _check_access(db: AsyncSession, user: User, cp_id: UUID) -> None:
    """Проверка доступа к КП. Клиент видит только КП по своим заявкам (не draft)."""
    cp = await svc.get_proposal(db, cp_id)
    if cp is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="КП не найдено",
        )
    if user.role in (UserRole.HEAD, UserRole.ADMIN):
        return
    if user.role == UserRole.MANAGER:
        m = (
            await db.execute(select(Manager).where(Manager.user_id == user.id))
        ).scalar_one_or_none()
        if m is None or cp.manager_id != m.id:
            raise ProblemException(
                status_code=status.HTTP_403_FORBIDDEN,
                title="Forbidden",
                detail="Это не ваше КП",
            )
        return
    # client
    client = (
        await db.execute(select(Client).where(Client.user_id == user.id))
    ).scalar_one_or_none()
    req = await requests_svc.get_request(db, cp.request_id)
    if client is None or req is None or req.client_id != client.id:
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Нет доступа к этому КП",
        )
    if cp.status == CPStatus.DRAFT:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="КП ещё не отправлено клиенту",
        )


@router.get("", response_model=Page[CPListItem])
async def list_proposals(
    status_filter: CPStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[CPListItem]:
    rows, total = await svc.list_for_user(
        db, user, status=status_filter, limit=limit, offset=offset
    )
    items = [
        CPListItem(
            id=r["cp"].id,
            cp_number=r["cp"].cp_number,
            request_id=r["cp"].request_id,
            request_number=r["request_number"],
            client_company=r["client_company"],
            manager_id=r["cp"].manager_id,
            manager_name=r["manager_name"],
            status=r["cp"].status,
            valid_until=r["cp"].valid_until,
            total_amount=r["cp"].total_amount,
            version=r["cp"].version,
            created_at=r["cp"].created_at,
            sent_at=r["cp"].sent_at,
        )
        for r in rows
    ]
    return Page[CPListItem](items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/from-request/{request_id}",
    response_model=CPDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_from_request(
    request_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_above),
) -> CPDetail:
    req = await requests_svc.get_request(db, request_id)
    if req is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Заявка не найдена",
        )
    # Заявка должна быть «в работе» или в «требуется доработка»
    from app.models.enums import RequestStatus

    if req.status not in (RequestStatus.IN_PROGRESS, RequestStatus.REVISION_NEEDED):
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail="КП можно создать только для заявки в статусе 'в работе' или 'требуется доработка'",
        )
    manager = (
        await db.execute(select(Manager).where(Manager.user_id == actor.id))
    ).scalar_one_or_none()
    if manager is None and actor.role == UserRole.MANAGER:
        raise ProblemException(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail="У пользователя нет записи менеджера",
        )
    if manager is None:
        # для head/admin — пробуем найти менеджера заявки
        if req.manager_id is None:
            raise ProblemException(
                status_code=status.HTTP_409_CONFLICT,
                title="Conflict",
                detail="Сначала закрепите менеджера за заявкой",
            )
        manager = (
            await db.execute(select(Manager).where(Manager.id == req.manager_id))
        ).scalar_one_or_none()

    try:
        cp = await svc.create_draft_from_request(db, req, manager)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=actor.id,
        action="cp.create_draft",
        entity_type="cp",
        entity_id=cp.id,
        details={"cp_number": cp.cp_number, "request_id": str(req.id)},
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, cp.id)


@router.get("/by-request/{request_id}", response_model=CPDetail | None)
async def get_by_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CPDetail | None:
    cp = await svc.get_proposal_by_request(db, request_id)
    if cp is None:
        return None
    await _check_access(db, user, cp.id)
    return await _build_detail(db, cp.id)


@router.get("/{cp_id}", response_model=CPDetail)
async def get_proposal(
    cp_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CPDetail:
    await _check_access(db, user, cp_id)
    return await _build_detail(db, cp_id)


@router.get("/{cp_id}/pdf")
async def get_proposal_pdf(
    cp_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """ФТ-06-03 — генерация коммерческого предложения в формате PDF."""
    await _check_access(db, user, cp_id)

    cp = (
        await db.execute(
            select(CommercialProposal)
            .options(selectinload(CommercialProposal.items))
            .where(CommercialProposal.id == cp_id)
        )
    ).scalar_one_or_none()
    if cp is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Коммерческое предложение не найдено",
        )

    # Подгружаем связанные сущности для шапки и подвала
    request = (
        await db.execute(select(ReqModel).where(ReqModel.id == cp.request_id))
    ).scalar_one_or_none()
    client = None
    if request is not None:
        client = (
            await db.execute(select(Client).where(Client.id == request.client_id))
        ).scalar_one_or_none()
    manager_name: str | None = None
    if cp.manager_id:
        manager_name = (
            await db.execute(
                select(User.full_name)
                .join(Manager, Manager.user_id == User.id)
                .where(Manager.id == cp.manager_id)
            )
        ).scalar_one_or_none()

    # Сортируем позиции стабильно (по id)
    sorted_items = sorted(cp.items, key=lambda i: str(i.id))
    pdf_items = [
        CPItemData(
            index=idx,
            article=None,  # в модели CPItem нет артикула, есть только name
            name=it.name,
            quantity=it.quantity,
            unit_price=it.unit_price,
            discount_percent=it.discount_percent,
            line_total=it.total_price,
        )
        for idx, it in enumerate(sorted_items, start=1)
    ]

    pdf_bytes = render_proposal_pdf(
        cp_number=cp.cp_number,
        version=cp.version,
        created_at=cp.created_at.strftime("%d.%m.%Y %H:%M"),
        valid_until=cp.valid_until.strftime("%d.%m.%Y") if cp.valid_until else None,
        seller_company="ООО «АвтоДеталь»",
        seller_inn="7700000000",
        client_company=client.company_name if client else "—",
        client_inn=client.inn if client else "—",
        client_kpp=client.kpp if client else None,
        items=pdf_items,
        total_amount=cp.total_amount or 0,
        payment_terms=cp.payment_terms,
        delivery_terms=cp.delivery_terms,
        manager_name=manager_name,
    )

    filename = f"KP-{cp.cp_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )


@router.patch("/{cp_id}", response_model=CPDetail)
async def update_proposal(
    cp_id: UUID,
    payload: CPDraftUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_above),
) -> CPDetail:
    await _check_access(db, actor, cp_id)
    cp = await svc.get_proposal(db, cp_id)
    if cp is None:
        raise ProblemException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="КП не найдено",
        )

    try:
        items_payload = (
            [u.model_dump() for u in payload.items] if payload.items else None
        )
        add_payload = (
            [a.model_dump() for a in payload.items_to_add]
            if payload.items_to_add
            else None
        )
        await svc.update_draft(
            db,
            cp,
            items_updates=items_payload,
            items_to_remove=payload.items_to_remove,
            items_to_add=add_payload,
            payment_terms=payload.payment_terms,
            delivery_terms=payload.delivery_terms,
            valid_until=payload.valid_until,
        )
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e

    await log_action(
        db,
        user_id=actor.id,
        action="cp.update",
        entity_type="cp",
        entity_id=cp.id,
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, cp_id)


@router.post("/{cp_id}/send", response_model=CPDetail)
async def send_proposal(
    cp_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(manager_or_above),
) -> CPDetail:
    await _check_access(db, actor, cp_id)
    cp = await svc.get_proposal(db, cp_id)
    req = await requests_svc.get_request(db, cp.request_id)
    try:
        await svc.send_proposal(db, cp, req)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e
    await log_action(
        db,
        user_id=actor.id,
        action="cp.send",
        entity_type="cp",
        entity_id=cp.id,
        details={"cp_number": cp.cp_number},
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, cp_id)


@router.post("/{cp_id}/accept", response_model=CPDetail)
async def accept_proposal(
    cp_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> CPDetail:
    await _check_access(db, user, cp_id)
    cp = await svc.get_proposal(db, cp_id)
    req = await requests_svc.get_request(db, cp.request_id)
    try:
        await svc.accept_proposal(db, cp, req)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e
    await log_action(
        db,
        user_id=user.id,
        action="cp.accept",
        entity_type="cp",
        entity_id=cp.id,
        details={"cp_number": cp.cp_number},
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, cp_id)


@router.post("/{cp_id}/reject", response_model=CPDetail)
async def reject_proposal(
    cp_id: UUID,
    payload: CPRejectIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> CPDetail:
    await _check_access(db, user, cp_id)
    cp = await svc.get_proposal(db, cp_id)
    req = await requests_svc.get_request(db, cp.request_id)
    try:
        await svc.reject_proposal(db, cp, req)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e
    await log_action(
        db,
        user_id=user.id,
        action="cp.reject",
        entity_type="cp",
        entity_id=cp.id,
        details={"cp_number": cp.cp_number, "reason": payload.reason},
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, cp_id)


@router.post("/{cp_id}/revision", response_model=CPDetail)
async def request_revision(
    cp_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(client_only),
) -> CPDetail:
    await _check_access(db, user, cp_id)
    cp = await svc.get_proposal(db, cp_id)
    req = await requests_svc.get_request(db, cp.request_id)
    try:
        await svc.revision_request(db, cp, req)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=str(e),
        ) from e
    await log_action(
        db,
        user_id=user.id,
        action="cp.revision",
        entity_type="cp",
        entity_id=cp.id,
        details={"cp_number": cp.cp_number},
        ip_address=_ip(request),
    )
    await db.commit()
    return await _build_detail(db, cp_id)
