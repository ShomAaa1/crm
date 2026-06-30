# АвтоДеталь CRM

CRM-система для оптового поставщика автозапчастей. Автоматизирует сквозной процесс
продаж: от заявки клиента до закрытия сделки, с аналитикой для руководителя.
Дипломный проект.

## Стек

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2.x (async) + Alembic + Pydantic v2
- **БД:** PostgreSQL 16
- **Кэш:** Redis 7 (refresh-токены, сессии)
- **Frontend:** React 18 + TypeScript + Vite + Tailwind + Zustand + recharts
- **Auth:** JWT (access + refresh) с RBAC (4 роли: client, manager, head, admin)
- **Веб-сервер:** nginx (раздача статики, reverse proxy, TLS)
- **Контейнеризация:** Docker Compose

## Возможности

- Личный кабинет клиента: каталог с поиском, корзина, оформление заявок
- Сквозной процесс **«заявка → коммерческое предложение → заказ»** с автосозданием заказа
- Формирование КП со скидками и генерацией PDF (ReportLab)
- Машина состояний заказа (создан → подтверждён → отгружен → доставлен / отменён)
  со списанием и возвратом складских остатков
- Распределение заявок: автоназначение, общая очередь, назначение руководителем
- Аналитический дашборд: KPI с динамикой, воронка продаж, рейтинг менеджеров, экспорт в Excel
- Карточка клиента с хронологией взаимодействий и поиском дублей по ИНН
- Постановка корректирующих задач менеджерам
- Админ-панель: управление пользователями и каталогом
- Ролевое разграничение доступа, JWT-аутентификация, журнал аудита

## Архитектура

Трёхзвенная архитектура, разворачивается через Docker Compose как **4 контейнера**:

| Контейнер | Роль |
|-----------|------|
| `postgres` | основная база данных |
| `redis` | refresh-токены и кэш |
| `backend` | приложение FastAPI |
| `nginx` | раздаёт собранный фронтенд, проксирует API, терминирует TLS (HTTPS) |

Контейнер nginx собирается многоэтапно: на этапе сборки фронтенд компилируется в
статические файлы, которые затем раздаёт nginx. Frontend отдельным контейнером не запускается.

## Быстрый старт

```bash
# 1. Скопировать env-файл
cp .env.example .env

# 2. Собрать и поднять всё окружение
#    (миграции применятся автоматически при старте backend)
docker compose up --build

# 3. В отдельном терминале — наполнить БД базовыми seed-данными
docker compose exec backend python -m scripts.seed

# 4. (опционально) Наполнить демо-данными для дашборда
#    (исторические сделки за 60 дней — чтобы заполнились KPI и дельты)
docker compose exec backend python -m scripts.seed_dashboard

# 5. Открыть в браузере
open https://localhost
```

> ⚠️ Сертификат самоподписанный — браузер предупредит о небезопасности.
> Для локального запуска это нормально: «Дополнительно → Перейти на localhost».

## Демо-учётки (после `seed`)

| Роль     | Email                      | Пароль        |
|----------|----------------------------|---------------|
| admin    | admin@autodetail.ru        | Admin123!     |
| head     | head@autodetail.ru         | Head123!      |
| manager  | manager1@autodetail.ru     | Manager123!   |
| client   | client1@autodetail.ru      | Client123!    |

## Полезные команды

```bash
# Статус контейнеров
docker compose ps

# Логи бэкенда
docker compose logs -f backend

# Применить миграции вручную
docker compose exec backend alembic upgrade head

# Создать новую миграцию (после правок моделей)
docker compose exec backend alembic revision --autogenerate -m "описание"

# Тесты
docker compose exec backend pytest

# Подключиться к БД
docker compose exec postgres psql -U autodetail -d autodetail

# Остановить (с -v — со стиранием данных БД)
docker compose down
```

## Структура

```
autodetail-crm/
├── backend/        # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── models/      # ORM-модели (11 сущностей предметной области)
│   │   ├── schemas/     # Pydantic-схемы
│   │   ├── routers/     # API endpoints
│   │   ├── services/    # Бизнес-логика
│   │   ├── middleware/  # Auth, RBAC, RFC 7807
│   │   └── utils/       # Хеши, JWT, валидаторы
│   ├── alembic/         # Миграции
│   └── scripts/         # seed.py, seed_dashboard.py
├── frontend/       # React + Vite
│   └── src/
│       ├── api/         # axios + interceptors
│       ├── store/       # zustand
│       ├── pages/       # страницы по ролям
│       └── components/
├── nginx/          # Dockerfile (многоэтапная сборка) + nginx.conf
└── docker-compose.yml
```

## Этапы разработки

- [x] **Этап 1:** Фундамент — Docker, БД, миграции, JWT+RBAC, CRUD пользователей
- [x] **Этап 2:** Каталог + корзина
- [x] **Этап 3:** Заявки + КП
- [x] **Этап 4:** Сделки + заказы
- [x] **Этап 5:** Аналитика (дашборд KPI)
- [x] **Этап 6:** Финализация (тесты, аудит, документация)
