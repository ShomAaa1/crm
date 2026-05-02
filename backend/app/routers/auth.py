from fastapi import APIRouter, Depends, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.problem import ProblemException
from app.models import User
from app.schemas.auth import LoginIn, MeOut, RefreshIn, TokenPair, UserOut
from app.services import auth as auth_service
from app.services.audit import log_action
from app.utils.security import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        await log_action(
            db,
            user_id=user.id if user else None,
            action="auth.login_failed",
            entity_type="user",
            entity_id=user.id if user else None,
            details={"email": payload.email},
            ip_address=_client_ip(request),
            commit=True,
        )
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Неверный email или пароль",
        )

    if not user.is_active:
        raise ProblemException(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail="Пользователь заблокирован",
        )

    access, expires_in = auth_service.create_access_token(user.id, user.role.value)
    refresh, jti = auth_service.create_refresh_token(user.id)
    await auth_service.store_refresh(jti, user.id)

    await log_action(
        db,
        user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        ip_address=_client_ip(request),
        commit=True,
    )

    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    try:
        decoded = auth_service.decode_refresh_token(payload.refresh_token)
    except JWTError as e:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail=f"Недействительный refresh-токен: {e}",
        ) from e

    jti = decoded.get("jti")
    sub = decoded.get("sub")
    if not jti or not sub:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Refresh-токен повреждён",
        )

    if not await auth_service.is_refresh_active(jti):
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Refresh-токен ревокирован или истёк",
        )

    from uuid import UUID

    user_id = UUID(sub)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise ProblemException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Пользователь не найден или заблокирован",
        )

    # Rotation: ревокаем старый, выдаём новый
    await auth_service.revoke_refresh(jti)
    access, expires_in = auth_service.create_access_token(user.id, user.role.value)
    new_refresh, new_jti = auth_service.create_refresh_token(user.id)
    await auth_service.store_refresh(new_jti, user.id)

    return TokenPair(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    try:
        decoded = auth_service.decode_refresh_token(payload.refresh_token)
        jti = decoded.get("jti")
        if jti:
            await auth_service.revoke_refresh(jti)
    except JWTError:
        # Невалидный refresh — всё равно фиксируем logout, не падаем
        pass

    await log_action(
        db,
        user_id=user.id,
        action="auth.logout",
        entity_type="user",
        entity_id=user.id,
        ip_address=_client_ip(request),
        commit=True,
    )


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(get_current_user)) -> MeOut:
    return MeOut.model_validate(user)
