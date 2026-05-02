"""Idempotent seed: 1 admin + 1 head + 3 manager + 3 client.

Запуск: docker compose exec backend python -m scripts.seed
Если пользователь с таким email уже есть — пропускаем (skip).
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, engine
from app.models import Client, ClientContact, Manager, User
from app.models.enums import UserRole
from app.utils.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("seed")


SEED_USERS: list[dict] = [
    {
        "email": "admin@autodetail.ru",
        "password": "Admin123!",
        "role": UserRole.ADMIN,
        "full_name": "Администратор Системы",
        "phone": "+7 (495) 000-00-01",
    },
    {
        "email": "head@autodetail.ru",
        "password": "Head123!",
        "role": UserRole.HEAD,
        "full_name": "Иванов Иван Иванович",
        "phone": "+7 (495) 000-00-10",
        "manager": {"department": "Отдел продаж", "specialization": "Руководство"},
    },
    {
        "email": "manager1@autodetail.ru",
        "password": "Manager123!",
        "role": UserRole.MANAGER,
        "full_name": "Петров Пётр Петрович",
        "phone": "+7 (495) 000-00-11",
        "manager": {"department": "Отдел продаж", "specialization": "Иномарки"},
    },
    {
        "email": "manager2@autodetail.ru",
        "password": "Manager123!",
        "role": UserRole.MANAGER,
        "full_name": "Сидорова Анна Сергеевна",
        "phone": "+7 (495) 000-00-12",
        "manager": {"department": "Отдел продаж", "specialization": "Отечественные авто"},
    },
    {
        "email": "manager3@autodetail.ru",
        "password": "Manager123!",
        "role": UserRole.MANAGER,
        "full_name": "Кузнецов Алексей Викторович",
        "phone": "+7 (495) 000-00-13",
        "manager": {"department": "Отдел продаж", "specialization": "Грузовая техника"},
    },
    {
        "email": "client1@autodetail.ru",
        "password": "Client123!",
        "role": UserRole.CLIENT,
        "full_name": "Смирнов Дмитрий Олегович",
        "phone": "+7 (495) 100-10-01",
        "client": {
            "company_name": "ООО «АвтоМир»",
            "inn": "7707083893",
            "kpp": "770701001",
            "ogrn": "1027700132195",
            "legal_address": "г. Москва, ул. Тверская, д. 1",
            "delivery_address": "г. Москва, ул. Тверская, д. 1, склад 3",
            "credit_limit": Decimal("500000.00"),
            "contact": {
                "full_name": "Смирнов Дмитрий Олегович",
                "position": "Директор",
                "phone": "+7 (495) 100-10-01",
                "email": "client1@autodetail.ru",
            },
        },
    },
    {
        "email": "client2@autodetail.ru",
        "password": "Client123!",
        "role": UserRole.CLIENT,
        "full_name": "Михайлов Сергей Андреевич",
        "phone": "+7 (495) 100-10-02",
        "client": {
            "company_name": "ООО «ТехСервис»",
            "inn": "7736050003",
            "kpp": "773601001",
            "ogrn": "1027700070518",
            "legal_address": "г. Москва, Ленинский пр-т, д. 25",
            "delivery_address": "г. Москва, Ленинский пр-т, д. 25, бокс 7",
            "credit_limit": Decimal("300000.00"),
            "contact": {
                "full_name": "Михайлов Сергей Андреевич",
                "position": "Закупщик",
                "phone": "+7 (495) 100-10-02",
                "email": "client2@autodetail.ru",
            },
        },
    },
    {
        "email": "client3@autodetail.ru",
        "password": "Client123!",
        "role": UserRole.CLIENT,
        "full_name": "Васильева Ольга Николаевна",
        "phone": "+7 (495) 100-10-03",
        "client": {
            "company_name": "ИП Васильева О.Н.",
            "inn": "7702070139",
            "kpp": "770201001",
            "ogrn": "1027739609391",
            "legal_address": "г. Москва, Кутузовский пр-т, д. 12",
            "delivery_address": "г. Москва, Кутузовский пр-т, д. 12",
            "credit_limit": Decimal("150000.00"),
            "contact": {
                "full_name": "Васильева Ольга Николаевна",
                "position": "Индивидуальный предприниматель",
                "phone": "+7 (495) 100-10-03",
                "email": "client3@autodetail.ru",
            },
        },
    },
]


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def seed_users(db: AsyncSession) -> tuple[int, int]:
    created = 0
    skipped = 0

    head_manager_id = None

    for data in SEED_USERS:
        existing = await _get_user_by_email(db, data["email"])
        if existing is not None:
            logger.info("skip user %s (уже существует)", data["email"])
            skipped += 1
            if data["role"] == UserRole.HEAD:
                m = await db.execute(select(Manager).where(Manager.user_id == existing.id))
                head_existing = m.scalar_one_or_none()
                if head_existing:
                    head_manager_id = head_existing.id
            continue

        user = User(
            email=data["email"],
            password_hash=hash_password(data["password"]),
            role=data["role"],
            full_name=data["full_name"],
            phone=data.get("phone"),
            is_active=True,
        )
        db.add(user)
        await db.flush()

        if "manager" in data:
            mgr_data = data["manager"]
            manager = Manager(
                user_id=user.id,
                department=mgr_data.get("department"),
                specialization=mgr_data.get("specialization"),
                is_available=True,
                head_id=head_manager_id if data["role"] == UserRole.MANAGER else None,
            )
            db.add(manager)
            await db.flush()
            if data["role"] == UserRole.HEAD:
                head_manager_id = manager.id

        if "client" in data:
            cli_data = data["client"]
            client = Client(
                user_id=user.id,
                company_name=cli_data["company_name"],
                inn=cli_data["inn"],
                kpp=cli_data.get("kpp"),
                ogrn=cli_data.get("ogrn"),
                legal_address=cli_data.get("legal_address"),
                delivery_address=cli_data.get("delivery_address"),
                credit_limit=cli_data.get("credit_limit", Decimal("0")),
                debt=Decimal("0"),
            )
            db.add(client)
            await db.flush()

            contact = cli_data.get("contact")
            if contact:
                db.add(
                    ClientContact(
                        client_id=client.id,
                        full_name=contact["full_name"],
                        position=contact.get("position"),
                        phone=contact.get("phone"),
                        email=contact.get("email"),
                        is_primary=True,
                    )
                )

        logger.info("create user %s (%s)", data["email"], data["role"].value)
        created += 1

    await db.commit()
    return created, skipped


async def main() -> None:
    async with AsyncSessionLocal() as db:
        created, skipped = await seed_users(db)
    await engine.dispose()
    logger.info("Готово: создано %d, пропущено %d", created, skipped)


if __name__ == "__main__":
    asyncio.run(main())
