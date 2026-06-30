"""Создаёт демонстрационный заказ для скриншота карточки заказа.

Проходит реальную бизнес-цепочку через сервисный слой:
  заявка (NEW) → черновик КП → отправка КП → принятие КП → авто-создание заказа.

Заказ закрепляется за manager1@autodetail.ru (Петров Пётр Петрович)
и клиентом ООО «АвтоМир» (client1@autodetail.ru).

Идемпотентно: если у менеджера уже есть заказ — ничего не делает.

Запуск: docker compose exec backend python -m scripts.seed_order
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.database import AsyncSessionLocal, engine
from app.models import (
    Client,
    Manager,
    Order,
    Part,
    Request,
    RequestItem,
    User,
)
from app.models.enums import RequestStatus
from app.services import proposals as cp_svc
from app.services import requests as req_svc

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("seed_order")

MANAGER_EMAIL = "manager1@autodetail.ru"
CLIENT_EMAIL = "client1@autodetail.ru"

# Позиции будущего заказа: (артикул, количество)
ORDER_LINES: list[tuple[str, int]] = [
    ("BRE-P85020", 4),   # Колодки тормозные передние Brembo
    ("BRE-09A41311", 4), # Диск тормозной передний Brembo
    ("MOB-5W30-4", 6),   # Моторное масло Mobil 1 5W-30
    ("MAN-W7152", 6),    # Фильтр масляный Mann
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # --- менеджер ---
        manager = (
            await db.execute(
                select(Manager)
                .join(User, User.id == Manager.user_id)
                .where(User.email == MANAGER_EMAIL)
            )
        ).scalar_one_or_none()
        if manager is None:
            logger.error("Менеджер %s не найден — сначала запустите seed.py", MANAGER_EMAIL)
            return

        # идемпотентность: уже есть заказ у этого менеджера?
        existing = (
            await db.execute(
                select(func.count()).select_from(Order).where(Order.manager_id == manager.id)
            )
        ).scalar_one()
        if existing:
            logger.info("У менеджера уже есть %d заказ(ов) — пропускаю", existing)
            return

        # --- клиент ---
        client = (
            await db.execute(
                select(Client)
                .join(User, User.id == Client.user_id)
                .where(User.email == CLIENT_EMAIL)
            )
        ).scalar_one_or_none()
        if client is None:
            logger.error("Клиент %s не найден", CLIENT_EMAIL)
            return

        # --- позиции (запчасти) ---
        articles = [a for a, _ in ORDER_LINES]
        parts = {
            p.article: p
            for p in (
                await db.execute(select(Part).where(Part.article.in_(articles)))
            ).scalars().all()
        }

        # --- 1. Заявка (NEW), закреплена за менеджером ---
        number = await req_svc._next_request_number(db)
        request = Request(
            request_number=number,
            client_id=client.id,
            manager_id=manager.id,
            status=RequestStatus.NEW,
            comment="Плановое ТО автопарка: тормоза + замена масла",
            taken_at=datetime.now(timezone.utc),
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(request)
        await db.flush()

        for article, qty in ORDER_LINES:
            part = parts.get(article)
            if part is None:
                logger.warning("Запчасть %s не найдена — пропускаю строку", article)
                continue
            db.add(
                RequestItem(
                    request_id=request.id,
                    part_id=part.id,
                    description=f"{part.article} — {part.name}",
                    quantity=qty,
                    price_at_moment=part.price,
                )
            )
        await db.flush()
        logger.info("Заявка %s создана", request.request_number)

        # --- 2. Черновик КП из позиций заявки ---
        cp = await cp_svc.create_draft_from_request(db, request, manager)

        # --- 3. Условия + небольшая оптовая скидка 5% по всем позициям ---
        cp_items = await cp_svc.load_items(db, cp.id)
        items_updates = [
            {
                "id": ci.id,
                "quantity": ci.quantity,
                "unit_price": ci.unit_price,
                "discount_percent": Decimal("5"),
            }
            for ci, _ in cp_items
        ]
        await cp_svc.update_draft(
            db,
            cp,
            items_updates=items_updates,
            items_to_remove=None,
            payment_terms="Оплата по счёту в течение 5 рабочих дней после получения товара",
            delivery_terms="Самовывоз со склада поставщика либо доставка по согласованию",
            valid_until=None,
        )
        logger.info("КП %s сформировано (сумма %s ₽)", cp.cp_number, cp.total_amount)

        # --- 4. Отправка КП клиенту ---
        await cp_svc.send_proposal(db, cp, request)

        # --- 5. Принятие КП → авто-создание заказа ---
        await cp_svc.accept_proposal(db, cp, request)
        await db.commit()

        order = (
            await db.execute(select(Order).where(Order.cp_id == cp.id))
        ).scalar_one_or_none()
        if order is None:
            logger.error("Заказ не создан — проверьте позиции КП")
            return

        logger.info(
            "ГОТОВО: заказ %s, статус %s, сумма %s ₽, менеджер %s",
            order.order_number,
            order.status.value,
            order.total_amount,
            MANAGER_EMAIL,
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
