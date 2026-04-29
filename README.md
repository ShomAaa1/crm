# АвтоДеталь CRM

CRM-система для оптового поставщика автозапчастей. Дипломный проект.

## Стек

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2.x (async) + Alembic + Pydantic v2
- **БД:** PostgreSQL 16
- **Кэш:** Redis 7 (refresh-токены, сессии)
- **Frontend:** React 18 + TypeScript + Vite + Tailwind + Zustand
- **Auth:** JWT (access + refresh) с RBAC (4 роли: client, manager, head, admin)
- **Контейнеризация:** Docker Compose

## Быстрый старт

```bash
# 1. Скопировать env-файл
cp .env.example .env

# 2. Поднять всё окружение (миграции применятся автоматически при старте backend)
docker compose up --build

# 3. В отдельном терминале — наполнить БД seed-данными
docker compose exec backend python -m scripts.seed

# 4. Открыть фронт
open http://localhost:5173
```

## Демо-учётки (после `seed`)

| Роль     | Email                      | Пароль        |
|----------|----------------------------|---------------|
| admin    | admin@autodetail.ru        | Admin123!     |
| head     | head@autodetail.ru         | Head123!      |
| manager  | manager1@autodetail.ru     | Manager123!   |
| client   | client1@autodetail.ru      | Client123!    |

## Полезные команды

```bash
# Применить миграции вручную
docker compose exec backend alembic upgrade head

# Создать новую миграцию (после правок моделей)
docker compose exec backend alembic revision --autogenerate -m "описание"

# Тесты
docker compose exec backend pytest

# Подключиться к БД
docker compose exec postgres psql -U autodetail -d autodetail
```

## Структура

```
autodetail-crm/
├── backend/        # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── models/      # ORM-модели (все 17 таблиц)
│   │   ├── schemas/     # Pydantic-схемы
│   │   ├── routers/     # API endpoints
│   │   ├── services/    # Бизнес-логика
│   │   ├── middleware/  # Auth, RBAC, RFC 7807
│   │   └── utils/       # Хеши, JWT, валидаторы
│   ├── alembic/         # Миграции
│   └── scripts/         # seed.py
├── frontend/       # React + Vite
│   └── src/
│       ├── api/         # axios + interceptors
│       ├── store/       # zustand
│       ├── pages/       # страницы по ролям
│       └── components/
└── docker-compose.yml
```

## Этапы разработки

- [x] **Этап 1:** Фундамент — Docker, БД, миграции, JWT+RBAC, CRUD пользователей
- [ ] **Этап 2:** Каталог + корзина
- [ ] **Этап 3:** Запросы + КП
- [ ] **Этап 4:** Сделки + заказы
- [ ] **Этап 5:** Аналитика (дашборд KPI)
- [ ] **Этап 6:** Финализация (тесты, аудит, документация)
