from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# 规定用户传什么进来
class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr | None = None

    @field_validator("email")  # Pydantic 字段验证器
    @classmethod  # 表明该方法属于类本身，而不是类的实例对象
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().casefold() if value is not None else None


# 规定服务器返回什么出去
class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    email: str | None = None
    email_verified_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class UserRoleUpdate(BaseModel):
    role: str


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserAdminResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )
