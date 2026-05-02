"""JWT + refresh-токены в Redis.

Refresh-токены: ключ `refresh:{jti}` со значением user_id, TTL = REFRESH_TOKEN_EXPIRE_DAYS.
Обратный индекс: `user_refresh:{user_id}` — Redis SET со всеми jti пользователя
(нужен для массового revoke при block/смене пароля).
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from jose import JWTError, jwt

from app.config import settings
from app.utils.redis import get_redis

ACCESS = "access"
REFRESH = "refresh"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: UUID, role: str) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = _now() + expires_delta
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": ACCESS,
        "iat": int(_now().timestamp()),
        "exp": int(expire.timestamp()),
        "jti": uuid4().hex,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def create_refresh_token(user_id: UUID) -> tuple[str, str]:
    """Возвращает (token, jti)."""
    jti = uuid4().hex
    expire = _now() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": REFRESH,
        "iat": int(_now().timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


async def store_refresh(jti: str, user_id: UUID) -> None:
    redis = get_redis()
    ttl = settings.refresh_token_expire_days * 86400
    pipe = redis.pipeline()
    pipe.set(f"refresh:{jti}", str(user_id), ex=ttl)
    pipe.sadd(f"user_refresh:{user_id}", jti)
    pipe.expire(f"user_refresh:{user_id}", ttl)
    await pipe.execute()


async def revoke_refresh(jti: str) -> None:
    redis = get_redis()
    user_id = await redis.get(f"refresh:{jti}")
    pipe = redis.pipeline()
    pipe.delete(f"refresh:{jti}")
    if user_id:
        pipe.srem(f"user_refresh:{user_id}", jti)
    await pipe.execute()


async def revoke_all_user_refreshes(user_id: UUID) -> int:
    """Ревокает все refresh-токены пользователя. Возвращает количество удалённых."""
    redis = get_redis()
    key = f"user_refresh:{user_id}"
    jtis = await redis.smembers(key)
    if not jtis:
        return 0
    pipe = redis.pipeline()
    for jti in jtis:
        pipe.delete(f"refresh:{jti}")
    pipe.delete(key)
    await pipe.execute()
    return len(jtis)


async def is_refresh_active(jti: str) -> bool:
    redis = get_redis()
    return await redis.exists(f"refresh:{jti}") == 1


def decode_token(token: str) -> dict:
    """Декодирует JWT. Бросает JWTError при невалидной подписи или истечении."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def decode_access_token(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("type") != ACCESS:
        raise JWTError("Wrong token type, expected access")
    return payload


def decode_refresh_token(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("type") != REFRESH:
        raise JWTError("Wrong token type, expected refresh")
    return payload
