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
from app.models import Category, Client, ClientContact, Manager, Part, PriceHistory, User
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


SEED_CATEGORIES: list[dict] = [
    # верхний уровень
    {"name": "Двигатель", "slug": "engine", "parent": None},
    {"name": "Тормозная система", "slug": "brakes", "parent": None},
    {"name": "Подвеска", "slug": "suspension", "parent": None},
    {"name": "Электрика", "slug": "electrics", "parent": None},
    {"name": "Кузов и оптика", "slug": "body-and-lights", "parent": None},
    # подкатегории
    {"name": "Масла и фильтры", "slug": "engine-oils-filters", "parent": "engine"},
    {"name": "Поршневая группа", "slug": "engine-pistons", "parent": "engine"},
    {"name": "Тормозные колодки", "slug": "brake-pads", "parent": "brakes"},
    {"name": "Тормозные диски", "slug": "brake-discs", "parent": "brakes"},
    {"name": "Амортизаторы", "slug": "shock-absorbers", "parent": "suspension"},
    {"name": "Аккумуляторы", "slug": "batteries", "parent": "electrics"},
    {"name": "Фары и лампы", "slug": "headlights", "parent": "body-and-lights"},
]


SEED_PARTS: list[dict] = [
    # масла и фильтры
    {
        "article": "MOB-5W30-4",
        "name": "Моторное масло Mobil 1 ESP 5W-30, 4 л",
        "manufacturer": "Mobil",
        "category_slug": "engine-oils-filters",
        "price": Decimal("3890.00"),
        "stock": 45,
    },
    {
        "article": "SHE-5W40-4",
        "name": "Моторное масло Shell Helix Ultra 5W-40, 4 л",
        "manufacturer": "Shell",
        "category_slug": "engine-oils-filters",
        "price": Decimal("3450.00"),
        "stock": 38,
    },
    {
        "article": "MAN-W7152",
        "name": "Фильтр масляный Mann W 712/52",
        "manufacturer": "Mann-Filter",
        "category_slug": "engine-oils-filters",
        "price": Decimal("520.00"),
        "stock": 120,
    },
    {
        "article": "MAN-C25114",
        "name": "Фильтр воздушный Mann C 25 114",
        "manufacturer": "Mann-Filter",
        "category_slug": "engine-oils-filters",
        "price": Decimal("780.00"),
        "stock": 64,
    },
    # поршневая группа
    {
        "article": "MAH-021PI2417",
        "name": "Кольца поршневые Mahle 021 PI 24170",
        "manufacturer": "Mahle",
        "category_slug": "engine-pistons",
        "price": Decimal("4200.00"),
        "stock": 18,
    },
    # колодки
    {
        "article": "BRE-P85020",
        "name": "Колодки тормозные передние Brembo P85020",
        "manufacturer": "Brembo",
        "category_slug": "brake-pads",
        "price": Decimal("3650.00"),
        "stock": 30,
    },
    {
        "article": "TRW-GDB1330",
        "name": "Колодки тормозные передние TRW GDB1330",
        "manufacturer": "TRW",
        "category_slug": "brake-pads",
        "price": Decimal("2380.00"),
        "stock": 52,
    },
    {
        "article": "BOS-0986494419",
        "name": "Колодки тормозные задние Bosch 0986494419",
        "manufacturer": "Bosch",
        "category_slug": "brake-pads",
        "price": Decimal("1990.00"),
        "stock": 41,
    },
    # диски
    {
        "article": "BRE-09A41311",
        "name": "Диск тормозной передний Brembo 09.A411.11",
        "manufacturer": "Brembo",
        "category_slug": "brake-discs",
        "price": Decimal("5240.00"),
        "stock": 22,
    },
    {
        "article": "ATE-24013002441",
        "name": "Диск тормозной задний ATE 24.0130-0244.1",
        "manufacturer": "ATE",
        "category_slug": "brake-discs",
        "price": Decimal("3120.00"),
        "stock": 28,
    },
    # амортизаторы
    {
        "article": "KYB-339713",
        "name": "Амортизатор передний KYB Excel-G 339713",
        "manufacturer": "KYB",
        "category_slug": "shock-absorbers",
        "price": Decimal("4890.00"),
        "stock": 24,
    },
    {
        "article": "SAC-553818",
        "name": "Амортизатор задний Sachs 553818",
        "manufacturer": "Sachs",
        "category_slug": "shock-absorbers",
        "price": Decimal("3950.00"),
        "stock": 19,
    },
    {
        "article": "MON-G7822",
        "name": "Амортизатор передний Monroe G7822",
        "manufacturer": "Monroe",
        "category_slug": "shock-absorbers",
        "price": Decimal("4150.00"),
        "stock": 0,
    },
    # аккумуляторы
    {
        "article": "VAR-E11",
        "name": "Аккумулятор Varta Blue Dynamic E11, 74 Ач",
        "manufacturer": "Varta",
        "category_slug": "batteries",
        "price": Decimal("9450.00"),
        "stock": 16,
    },
    {
        "article": "BOS-S40-08",
        "name": "Аккумулятор Bosch S4 008, 74 Ач",
        "manufacturer": "Bosch",
        "category_slug": "batteries",
        "price": Decimal("8990.00"),
        "stock": 12,
    },
    {
        "article": "TUD-TB740",
        "name": "Аккумулятор Tudor High-Tech TB740, 74 Ач",
        "manufacturer": "Tudor",
        "category_slug": "batteries",
        "price": Decimal("7150.00"),
        "stock": 9,
    },
    # фары/лампы
    {
        "article": "OSR-64210NBS",
        "name": "Лампа Osram Night Breaker Silver H7 (пара)",
        "manufacturer": "Osram",
        "category_slug": "headlights",
        "price": Decimal("1380.00"),
        "stock": 75,
    },
    {
        "article": "PHI-12972XVPS2",
        "name": "Лампа Philips X-tremeVision H7 (пара)",
        "manufacturer": "Philips",
        "category_slug": "headlights",
        "price": Decimal("1620.00"),
        "stock": 48,
    },
    {
        "article": "DEP-44115541LMLDEM1",
        "name": "Фара передняя левая DEPO 441-1554L-LD-EM1",
        "manufacturer": "DEPO",
        "category_slug": "headlights",
        "price": Decimal("8950.00"),
        "stock": 6,
    },
    {
        "article": "VAL-043677",
        "name": "Фара передняя правая Valeo 043677",
        "manufacturer": "Valeo",
        "category_slug": "headlights",
        "price": Decimal("12400.00"),
        "stock": 4,
    },
]


async def seed_categories(db: AsyncSession) -> tuple[int, int]:
    created = 0
    skipped = 0
    slug_to_id: dict[str, "UUID"] = {}

    # сначала верхний уровень, потом дети — на них ссылаемся
    ordered = sorted(SEED_CATEGORIES, key=lambda c: (c["parent"] is not None, c["slug"]))

    for data in ordered:
        existing = (
            await db.execute(select(Category).where(Category.slug == data["slug"]))
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("skip category %s", data["slug"])
            slug_to_id[data["slug"]] = existing.id
            skipped += 1
            continue

        parent_id = None
        if data["parent"]:
            parent_id = slug_to_id.get(data["parent"])
            if parent_id is None:
                parent = (
                    await db.execute(select(Category).where(Category.slug == data["parent"]))
                ).scalar_one_or_none()
                if parent:
                    parent_id = parent.id
                    slug_to_id[data["parent"]] = parent.id

        category = Category(name=data["name"], slug=data["slug"], parent_id=parent_id)
        db.add(category)
        await db.flush()
        slug_to_id[data["slug"]] = category.id
        logger.info("create category %s", data["slug"])
        created += 1

    await db.commit()
    return created, skipped


async def seed_parts(db: AsyncSession) -> tuple[int, int]:
    created = 0
    skipped = 0

    slugs = {data["category_slug"] for data in SEED_PARTS}
    cat_rows = (
        await db.execute(select(Category).where(Category.slug.in_(slugs)))
    ).scalars().all()
    slug_to_id = {c.slug: c.id for c in cat_rows}

    for data in SEED_PARTS:
        existing = (
            await db.execute(select(Part).where(Part.article == data["article"]))
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("skip part %s", data["article"])
            skipped += 1
            continue

        part = Part(
            article=data["article"],
            name=data["name"],
            manufacturer=data.get("manufacturer"),
            category_id=slug_to_id.get(data["category_slug"]),
            price=data["price"],
            stock_quantity=data.get("stock", 0),
            unit=data.get("unit", "шт"),
            is_active=True,
        )
        db.add(part)
        await db.flush()
        db.add(
            PriceHistory(
                part_id=part.id,
                old_price=None,
                new_price=part.price,
                changed_by=None,
            )
        )
        await db.flush()
        logger.info("create part %s", data["article"])
        created += 1

    await db.commit()
    return created, skipped


async def main() -> None:
    async with AsyncSessionLocal() as db:
        users_created, users_skipped = await seed_users(db)
        cats_created, cats_skipped = await seed_categories(db)
        parts_created, parts_skipped = await seed_parts(db)
    await engine.dispose()
    logger.info(
        "Готово: users %d/%d, categories %d/%d, parts %d/%d (created/skipped)",
        users_created, users_skipped,
        cats_created, cats_skipped,
        parts_created, parts_skipped,
    )


if __name__ == "__main__":
    asyncio.run(main())
