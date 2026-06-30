"""Демо-данные для аналитического дашборда.

Создаёт исторические цепочки «заявка → КП → заказ» с датами, размазанными
по последним 60 дням, чтобы на дашборде заполнились и текущий, и предыдущий
период (иначе дельты показывают «нет данных за прошлый период»).

Метрики дашборда считаются по:
  - Order.delivered_at  (выручка, число сделок, средний чек)
  - CommercialProposal.sent_at + status  (конверсия КП)

Запуск:  docker compose exec backend python -m scripts.seed_dashboard
Идемпотентно: если демо-данные уже есть (префикс DEMO-), скрипт выходит.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import (
    Client,
    CommercialProposal,
    CPItem,
    Manager,
    Order,
    OrderItem,
    Part,
    Request,
    RequestItem,
)
from app.models.enums import CPStatus, OrderStatus, RequestStatus

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("seed_dashboard")

DEALS = 60          # сколько демо-сделок создать
SPAN_DAYS = 60      # на сколько дней назад размазать (2 периода по 30 дней)
DEMO_PREFIX = "DEMO-"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # --- идемпотентность ---
        existing = (
            await db.execute(
                select(Request).where(Request.request_number.like(f"{DEMO_PREFIX}%")).limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("Демо-данные уже есть (префикс %s) — пропускаю.", DEMO_PREFIX)
            return

        clients = (await db.execute(select(Client))).scalars().all()
        managers = (await db.execute(select(Manager))).scalars().all()
        parts = (await db.execute(select(Part).where(Part.is_active == True))).scalars().all()  # noqa: E712

        if not clients or not managers or not parts:
            logger.error("Нет базовых данных. Сначала выполните: python -m scripts.seed")
            return

        now = datetime.now(timezone.utc)
        rng = random.Random(42)  # фиксированный seed → воспроизводимо

        n_orders = 0
        n_cps = 0
        for i in range(DEALS):
            client = rng.choice(clients)
            manager = rng.choice(managers)
            deal_parts = rng.sample(parts, k=min(rng.randint(1, 3), len(parts)))

            # дата сделки: 2..SPAN_DAYS дней назад (равномерно → оба периода заполнены)
            days_ago = rng.randint(2, SPAN_DAYS)
            deal_dt = now - timedelta(days=days_ago)

            # позиции и сумма
            lines: list[tuple[Part, int, Decimal, Decimal]] = []
            total = Decimal("0")
            for part in deal_parts:
                qty = rng.randint(1, 8)
                unit = Decimal(part.price)
                line_total = unit * qty
                total += line_total
                lines.append((part, qty, unit, line_total))

            # --- заявка ---
            req = Request(
                request_number=f"{DEMO_PREFIX}R-{i:04d}",
                client_id=client.id,
                manager_id=manager.id,
                status=RequestStatus.ACCEPTED,
            )
            db.add(req)
            await db.flush()
            for part, qty, unit, _ in lines:
                db.add(
                    RequestItem(
                        request_id=req.id,
                        part_id=part.id,
                        quantity=qty,
                        price_at_moment=unit,
                    )
                )

            # --- КП (исход сделки) ---
            # 65% принято → доставленный заказ; 25% отклонено; 10% отправлено (в работе)
            roll = rng.random()
            if roll < 0.65:
                cp_status = CPStatus.ACCEPTED
            elif roll < 0.90:
                cp_status = CPStatus.REJECTED
            else:
                cp_status = CPStatus.SENT

            cp = CommercialProposal(
                cp_number=f"{DEMO_PREFIX}CP-{i:04d}",
                request_id=req.id,
                manager_id=manager.id,
                status=cp_status,
                total_amount=total,
                sent_at=deal_dt,  # ← дата для конверсии
            )
            db.add(cp)
            await db.flush()
            for part, qty, unit, line_total in lines:
                db.add(
                    CPItem(
                        cp_id=cp.id,
                        part_id=part.id,
                        name=part.name,
                        quantity=qty,
                        unit_price=unit,
                        total_price=line_total,
                    )
                )
            n_cps += 1

            # --- заказ (только для принятых КП) ---
            if cp_status == CPStatus.ACCEPTED:
                # доставлен через 1..4 дня после отправки КП, но не позже «сейчас»
                delivered_dt = min(deal_dt + timedelta(days=rng.randint(1, 4)), now)
                order = Order(
                    order_number=f"{DEMO_PREFIX}O-{i:04d}",
                    client_id=client.id,
                    manager_id=manager.id,
                    cp_id=cp.id,
                    status=OrderStatus.DELIVERED,
                    total_amount=total,
                    delivery_address=client.delivery_address or "г. Демоград, демо-адрес",
                    delivered_at=delivered_dt,  # ← дата для выручки/сделок
                )
                db.add(order)
                await db.flush()
                for part, qty, unit, line_total in lines:
                    db.add(
                        OrderItem(
                            order_id=order.id,
                            part_id=part.id,
                            quantity=qty,
                            unit_price=unit,
                            total_price=line_total,
                        )
                    )
                req.status = RequestStatus.CLOSED_SUCCESS
                n_orders += 1
            elif cp_status == CPStatus.REJECTED:
                req.status = RequestStatus.REJECTED

        await db.commit()
        logger.info(
            "Готово: %d КП, из них %d доставленных заказов, размазано по %d дням.",
            n_cps,
            n_orders,
            SPAN_DAYS,
        )


if __name__ == "__main__":
    asyncio.run(main())
