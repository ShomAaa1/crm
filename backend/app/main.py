import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.middleware.problem import register_exception_handlers
from app.routers import auth, cart, categories, health, parts, requests, users
from app.utils.redis import get_redis

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("autodetail")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AutoDetail CRM API (env=%s)", settings.env)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection: OK")
    except Exception as e:
        logger.error("Database connection FAILED: %s", e)

    try:
        redis = get_redis()
        await redis.ping()
        logger.info("Redis connection: OK")
    except Exception as e:
        logger.error("Redis connection FAILED: %s", e)

    yield

    await engine.dispose()
    redis = get_redis()
    await redis.aclose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AutoDetail CRM API",
    version="0.1.0",
    description="B2B CRM для оптового поставщика автозапчастей",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

API_V1 = "/api/v1"

app.include_router(health.router, prefix=API_V1)
app.include_router(auth.router, prefix=API_V1)
app.include_router(users.router, prefix=API_V1)
app.include_router(categories.router, prefix=API_V1)
app.include_router(parts.router, prefix=API_V1)
app.include_router(cart.router, prefix=API_V1)
app.include_router(requests.router, prefix=API_V1)
