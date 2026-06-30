"""Дашборд для head — агрегированные счётчики."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models import (
    CommercialProposal,
    Manager,
    Order,
    Request,
    User,
)
from app.models.enums import CPStatus, OrderStatus, RequestStatus, UserRole

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

head_only = require_role(UserRole.HEAD)


class CounterItem(BaseModel):
    label: str
    value: int


class RevenuePoint(BaseModel):
    date: str  # ISO YYYY-MM-DD
    value: float


class ConversionPoint(BaseModel):
    month: str  # YYYY-MM
    conversion: float  # %


class FunnelStage(BaseModel):
    stage: str
    value: int
    conversion_pct: float | None = None  # % от предыдущей стадии


class ManagerScore(BaseModel):
    manager_name: str
    revenue: float
    deals_count: int


class DashboardSummary(BaseModel):
    # Период, к которому относятся агрегаты
    period_label: str  # "Последний день", "Последняя неделя", "С 01.01 по 30.06" и т.п.
    period_days: int  # Длина текущего периода в днях (для построения графиков)
    period_start: str  # ISO date YYYY-MM-DD
    period_end: str  # ISO date YYYY-MM-DD

    # Snapshot-показатели (не зависят от периода)
    requests_by_status: list[CounterItem]
    proposals_by_status: list[CounterItem]
    orders_by_status: list[CounterItem]
    sales_funnel: list[FunnelStage]
    active_requests: int
    total_clients: int
    total_managers: int

    # Показатели за выбранный период
    revenue_period: Decimal
    deals_won: int
    avg_deal_size: Decimal
    cp_conversion: float
    revenue_by_day: list[RevenuePoint]
    previous_revenue_by_day: list[RevenuePoint]  # эквивалентный предыдущий период
    manager_leaderboard: list[ManagerScore]

    # Δ к предыдущему периоду (в % или None если предыдущий = 0)
    revenue_delta_pct: float | None
    conversion_delta_pct: float | None
    deals_won_delta_pct: float | None
    avg_deal_size_delta_pct: float | None

    # Тренд за последние 6 месяцев (не зависит от выбранного периода)
    conversion_by_month: list[ConversionPoint]


REQ_STATUS_LABELS: dict[RequestStatus, str] = {
    RequestStatus.NEW: "Новые",
    RequestStatus.IN_PROGRESS: "В работе",
    RequestStatus.CP_SENT: "КП отправлено",
    RequestStatus.ACCEPTED: "Принято",
    RequestStatus.REJECTED: "Отклонено",
    RequestStatus.REVISION_NEEDED: "Доработка",
    RequestStatus.CLOSED_SUCCESS: "Закрыто успешно",
    RequestStatus.CLOSED_FAIL: "Закрыто неуспешно",
    RequestStatus.CANCELLED: "Отменено",
}

CP_STATUS_LABELS: dict[CPStatus, str] = {
    CPStatus.DRAFT: "Черновики",
    CPStatus.SENT: "Отправлены",
    CPStatus.ACCEPTED: "Приняты",
    CPStatus.REJECTED: "Отклонены",
    CPStatus.EXPIRED: "Истекли",
}

ORD_STATUS_LABELS: dict[OrderStatus, str] = {
    OrderStatus.CREATED: "Созданы",
    OrderStatus.CONFIRMED: "Подтверждены",
    OrderStatus.SHIPPED: "Отгружены",
    OrderStatus.DELIVERED: "Доставлены",
    OrderStatus.CANCELLED: "Отменены",
}


PERIOD_DAYS: dict[str, int] = {
    "day": 1,
    "week": 7,
    "month": 30,
    "quarter": 90,
    "year": 365,
}

PERIOD_LABELS: dict[str, str] = {
    "day": "Последний день",
    "week": "Последняя неделя",
    "month": "Последний месяц",
    "quarter": "Последний квартал",
    "year": "Последний год",
}


def _resolve_period(
    period: str | None, date_from: date | None, date_to: date | None
) -> tuple[datetime, datetime, datetime, datetime, str, int]:
    """Возвращает (curr_start, curr_end, prev_start, prev_end, label, days)."""
    now_dt = datetime.now(timezone.utc)

    # 1) Если задан кастомный диапазон — используем его
    if date_from is not None or date_to is not None:
        end_date = date_to or now_dt.date()
        start_date = date_from or (end_date - timedelta(days=30))
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        curr_end = datetime.combine(end_date, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        curr_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        period_days = max((curr_end - curr_start).days, 1)
        label = f"С {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"
        prev_end = curr_start
        prev_start = curr_start - timedelta(days=period_days)
        return curr_start, curr_end, prev_start, prev_end, label, period_days

    # 2) Иначе используем пресет (по умолчанию month)
    key = period or "month"
    if key not in PERIOD_DAYS:
        key = "month"
    period_days = PERIOD_DAYS[key]
    curr_end = now_dt
    curr_start = now_dt - timedelta(days=period_days)
    prev_end = curr_start
    prev_start = curr_start - timedelta(days=period_days)
    label = PERIOD_LABELS[key]
    return curr_start, curr_end, prev_start, prev_end, label, period_days


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    period: Literal["day", "week", "month", "quarter", "year"] | None = Query(
        default=None,
        description="Пресет периода (игнорируется, если задан date_from / date_to)",
    ),
    date_from: date | None = Query(
        default=None,
        description="Начало кастомного периода (YYYY-MM-DD)",
    ),
    date_to: date | None = Query(
        default=None,
        description="Конец кастомного периода (YYYY-MM-DD, включительно)",
    ),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(head_only),
) -> DashboardSummary:
    # Определение текущего и эквивалентного предыдущего периодов
    (
        period_curr_start,
        period_curr_end,
        period_prev_start,
        period_prev_end,
        period_label,
        period_days,
    ) = _resolve_period(period, date_from, date_to)

    # Заявки по статусам
    req_rows = (
        await db.execute(
            select(Request.status, func.count()).group_by(Request.status)
        )
    ).all()
    req_counts = {s: int(c) for s, c in req_rows}
    requests_by_status = [
        CounterItem(label=REQ_STATUS_LABELS[s], value=req_counts.get(s, 0))
        for s in RequestStatus
    ]

    # КП по статусам
    cp_rows = (
        await db.execute(
            select(CommercialProposal.status, func.count()).group_by(
                CommercialProposal.status
            )
        )
    ).all()
    cp_counts = {s: int(c) for s, c in cp_rows}
    proposals_by_status = [
        CounterItem(label=CP_STATUS_LABELS[s], value=cp_counts.get(s, 0))
        for s in CPStatus
    ]

    # Заказы по статусам
    ord_rows = (
        await db.execute(
            select(Order.status, func.count()).group_by(Order.status)
        )
    ).all()
    ord_counts = {s: int(c) for s, c in ord_rows}
    orders_by_status = [
        CounterItem(label=ORD_STATUS_LABELS[s], value=ord_counts.get(s, 0))
        for s in OrderStatus
    ]

    # Выручка и средний чек за выбранный период и эквивалентный предыдущий
    async def _revenue_and_deals(start: datetime, end: datetime) -> tuple[float, int]:
        row = (
            await db.execute(
                select(
                    func.coalesce(func.sum(Order.total_amount), 0),
                    func.count(),
                )
                .where(Order.status == OrderStatus.DELIVERED)
                .where(Order.delivered_at >= start)
                .where(Order.delivered_at < end)
            )
        ).one()
        return float(row[0] or 0), int(row[1] or 0)

    revenue_curr, deals_curr = await _revenue_and_deals(period_curr_start, period_curr_end)
    revenue_prev, deals_prev = await _revenue_and_deals(
        period_prev_start, period_prev_end
    )

    revenue = revenue_curr
    avg_deal_size_curr = (revenue_curr / deals_curr) if deals_curr > 0 else 0.0
    avg_deal_size_prev = (revenue_prev / deals_prev) if deals_prev > 0 else 0.0

    def _delta_pct(curr: float, prev: float) -> float | None:
        if prev <= 0:
            return None
        return round((curr - prev) / prev * 100, 1)

    revenue_delta_pct = _delta_pct(revenue_curr, revenue_prev)
    deals_won_delta_pct = _delta_pct(deals_curr, deals_prev)
    avg_deal_size_delta_pct = _delta_pct(avg_deal_size_curr, avg_deal_size_prev)

    # Выручка по дням — текущий и предыдущий 30-дневные периоды
    async def _daily_revenue(start: datetime, end: datetime) -> dict[str, float]:
        rows = (
            await db.execute(
                select(
                    func.date(Order.delivered_at).label("d"),
                    func.coalesce(func.sum(Order.total_amount), 0).label("sum"),
                )
                .where(Order.status == OrderStatus.DELIVERED)
                .where(Order.delivered_at >= start)
                .where(Order.delivered_at < end)
                .group_by(func.date(Order.delivered_at))
            )
        ).all()
        result: dict[str, float] = {}
        for d, s in rows:
            key = d.isoformat() if hasattr(d, "isoformat") else str(d)
            result[key] = float(s or 0)
        return result

    daily_curr = await _daily_revenue(period_curr_start, period_curr_end)
    daily_prev = await _daily_revenue(period_prev_start, period_prev_end)

    # Конечная дата текущего периода (включительно): для построения ряда
    curr_end_date = (period_curr_end - timedelta(seconds=1)).date()
    prev_end_date = (period_prev_end - timedelta(seconds=1)).date()
    revenue_by_day: list[RevenuePoint] = []
    for i in range(period_days - 1, -1, -1):
        day = curr_end_date - timedelta(days=i)
        revenue_by_day.append(
            RevenuePoint(date=day.isoformat(), value=daily_curr.get(day.isoformat(), 0.0))
        )

    previous_revenue_by_day: list[RevenuePoint] = []
    for i in range(period_days - 1, -1, -1):
        day = prev_end_date - timedelta(days=i)
        previous_revenue_by_day.append(
            RevenuePoint(date=day.isoformat(), value=daily_prev.get(day.isoformat(), 0.0))
        )

    # Конверсия КП: принятые / отправленные+
    accepted = cp_counts.get(CPStatus.ACCEPTED, 0)
    sent_total = (
        cp_counts.get(CPStatus.SENT, 0)
        + cp_counts.get(CPStatus.ACCEPTED, 0)
        + cp_counts.get(CPStatus.REJECTED, 0)
        + cp_counts.get(CPStatus.EXPIRED, 0)
    )
    conversion = (accepted / sent_total * 100) if sent_total > 0 else 0.0

    # Конверсия КП за два периода (для дельты)
    async def _conversion_in_period(start: datetime, end: datetime) -> float:
        row = (
            await db.execute(
                select(
                    func.count().filter(CommercialProposal.status == CPStatus.ACCEPTED),
                    func.count().filter(
                        CommercialProposal.status.in_(
                            (
                                CPStatus.SENT,
                                CPStatus.ACCEPTED,
                                CPStatus.REJECTED,
                                CPStatus.EXPIRED,
                            )
                        )
                    ),
                )
                .where(CommercialProposal.sent_at.is_not(None))
                .where(CommercialProposal.sent_at >= start)
                .where(CommercialProposal.sent_at < end)
            )
        ).one()
        acc_n = int(row[0] or 0)
        sent_n = int(row[1] or 0)
        return (acc_n / sent_n * 100) if sent_n > 0 else 0.0

    conv_curr = await _conversion_in_period(period_curr_start, period_curr_end)
    conv_prev = await _conversion_in_period(period_prev_start, period_prev_end)
    conversion_delta_pct = _delta_pct(conv_curr, conv_prev)

    # Конверсия КП по месяцам за последние 6 месяцев (для гистограммы)
    sent_statuses = (CPStatus.SENT, CPStatus.ACCEPTED, CPStatus.REJECTED, CPStatus.EXPIRED)
    today_dt = datetime.now(timezone.utc)
    # Начало периода = первое число месяца за 5 месяцев назад
    period_start_year = today_dt.year
    period_start_month = today_dt.month - 5
    while period_start_month <= 0:
        period_start_month += 12
        period_start_year -= 1
    period_start = datetime(
        period_start_year, period_start_month, 1, tzinfo=timezone.utc
    )

    month_expr = func.date_trunc("month", CommercialProposal.sent_at)
    monthly_rows = (
        await db.execute(
            select(
                month_expr.label("m"),
                CommercialProposal.status,
                func.count().label("cnt"),
            )
            .where(CommercialProposal.sent_at.is_not(None))
            .where(CommercialProposal.sent_at >= period_start)
            .where(CommercialProposal.status.in_(sent_statuses))
            .group_by(month_expr, CommercialProposal.status)
        )
    ).all()
    # ключ — "YYYY-MM"
    monthly_sent: dict[str, int] = {}
    monthly_accepted: dict[str, int] = {}
    for m, st, cnt in monthly_rows:
        key = f"{m.year:04d}-{m.month:02d}"
        monthly_sent[key] = monthly_sent.get(key, 0) + int(cnt)
        if st == CPStatus.ACCEPTED:
            monthly_accepted[key] = monthly_accepted.get(key, 0) + int(cnt)

    conversion_by_month: list[ConversionPoint] = []
    y, m = period_start_year, period_start_month
    for _ in range(6):
        key = f"{y:04d}-{m:02d}"
        sent_n = monthly_sent.get(key, 0)
        accepted_n = monthly_accepted.get(key, 0)
        conv = round(accepted_n / sent_n * 100, 1) if sent_n > 0 else 0.0
        conversion_by_month.append(ConversionPoint(month=key, conversion=conv))
        m += 1
        if m > 12:
            m = 1
            y += 1

    # Воронка продаж — кумулятивные счётчики прохождения по статусам.
    # Используем тот факт, что статусы линейны: NEW → IN_PROGRESS → CP_SENT
    # → ACCEPTED → CLOSED_SUCCESS (с альтернативными ветвями).
    def _req(*statuses: RequestStatus) -> int:
        return sum(req_counts.get(s, 0) for s in statuses)

    stage_all = _req(*RequestStatus)
    stage_in_work = _req(
        RequestStatus.IN_PROGRESS,
        RequestStatus.CP_SENT,
        RequestStatus.ACCEPTED,
        RequestStatus.REJECTED,
        RequestStatus.REVISION_NEEDED,
        RequestStatus.CLOSED_SUCCESS,
        RequestStatus.CLOSED_FAIL,
    )
    stage_cp_sent = _req(
        RequestStatus.CP_SENT,
        RequestStatus.ACCEPTED,
        RequestStatus.REJECTED,
        RequestStatus.REVISION_NEEDED,
        RequestStatus.CLOSED_SUCCESS,
        RequestStatus.CLOSED_FAIL,
    )
    stage_cp_accepted = _req(
        RequestStatus.ACCEPTED, RequestStatus.CLOSED_SUCCESS
    )
    stage_closed_won = _req(RequestStatus.CLOSED_SUCCESS)

    stage_values = [
        ("Все заявки", stage_all),
        ("В работе", stage_in_work),
        ("КП отправлено", stage_cp_sent),
        ("КП принято", stage_cp_accepted),
        ("Сделка закрыта", stage_closed_won),
    ]
    sales_funnel = []
    prev_value: int | None = None
    for stage, value in stage_values:
        if prev_value is None or prev_value == 0:
            conversion_pct = None
        else:
            conversion_pct = round(value / prev_value * 100, 1)
        sales_funnel.append(
            FunnelStage(stage=stage, value=value, conversion_pct=conversion_pct)
        )
        prev_value = value

    # Активные заявки = новые + в работе + ожидают ответа клиента
    active_requests = _req(
        RequestStatus.NEW,
        RequestStatus.IN_PROGRESS,
        RequestStatus.CP_SENT,
        RequestStatus.REVISION_NEEDED,
    )
    # Выигранные сделки
    # Сделок закрыто (по доставленным заказам) — за выбранный период
    deals_won = deals_curr

    # Счётчики пользователей
    total_clients = int(
        (
            await db.execute(
                select(func.count()).select_from(User).where(User.role == UserRole.CLIENT)
            )
        ).scalar_one()
    )
    total_managers = int(
        (
            await db.execute(
                select(func.count()).select_from(User).where(User.role == UserRole.MANAGER)
            )
        ).scalar_one()
    )

    # Топ-5 менеджеров по выручке за выбранный период
    leader_rows = (
        await db.execute(
            select(
                User.full_name,
                func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
                func.count(Order.id).label("deals"),
            )
            .join(Manager, Manager.id == Order.manager_id)
            .join(User, User.id == Manager.user_id)
            .where(Order.status == OrderStatus.DELIVERED)
            .where(Order.delivered_at >= period_curr_start)
            .where(Order.delivered_at < period_curr_end)
            .group_by(User.full_name)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(5)
        )
    ).all()
    manager_leaderboard = [
        ManagerScore(
            manager_name=name,
            revenue=float(rev or 0),
            deals_count=int(deals or 0),
        )
        for name, rev, deals in leader_rows
    ]

    return DashboardSummary(
        period_label=period_label,
        period_days=period_days,
        period_start=period_curr_start.date().isoformat(),
        period_end=curr_end_date.isoformat(),
        requests_by_status=requests_by_status,
        proposals_by_status=proposals_by_status,
        orders_by_status=orders_by_status,
        sales_funnel=sales_funnel,
        active_requests=active_requests,
        total_clients=total_clients,
        total_managers=total_managers,
        revenue_period=Decimal(str(round(revenue_curr, 2))),
        deals_won=deals_won,
        avg_deal_size=Decimal(str(round(avg_deal_size_curr, 2))),
        cp_conversion=round(conv_curr, 1),
        revenue_by_day=revenue_by_day,
        previous_revenue_by_day=previous_revenue_by_day,
        manager_leaderboard=manager_leaderboard,
        revenue_delta_pct=revenue_delta_pct,
        conversion_delta_pct=conversion_delta_pct,
        deals_won_delta_pct=deals_won_delta_pct,
        avg_deal_size_delta_pct=avg_deal_size_delta_pct,
        conversion_by_month=conversion_by_month,
    )
