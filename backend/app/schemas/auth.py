from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models import UserRole


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10)


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    full_name: str
    phone: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MeOut(UserOut):
    pass
