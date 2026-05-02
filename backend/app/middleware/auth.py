"""FastAPI-зависимости для аутентификации и RBAC."""

from uuid import UUID

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.problem import ProblemException
from app.models import User, UserRole
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Требуется авторизация",
        )
    try:
        payload = decode_access_token(token)
    except JWTError as e:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail=f"Недействительный токен: {e}",
        ) from e

    sub = payload.get("sub")
    if not sub:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Токен не содержит идентификатор пользователя",
        )

    try:
        user_id = UUID(sub)
    except ValueError as e:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Некорректный идентификатор пользователя",
        ) from e

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Пользователь не найден",
        )
    if not user.is_active:
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Пользователь заблокирован",
        )
    return user


def require_role(*roles: UserRole):
    """Фабрика зависимостей: разрешает доступ только пользователям с указанными ролями."""

    allowed = {r.value if isinstance(r, UserRole) else str(r) for r in roles}

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed:
            raise ProblemException(
                status_code=status.HTTP_403_FORBIDDEN,
                title="Forbidden",
                detail=f"Требуется одна из ролей: {', '.join(sorted(allowed))}",
            )
        return user

    return dependency
