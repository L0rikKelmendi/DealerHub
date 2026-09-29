"""User administration and audit schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.auth import UserOut


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = None
    role_names: list[str] = Field(default_factory=lambda: ["viewer"])


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=120)
    phone: str | None = None
    is_active: bool | None = None
    role_names: list[str] | None = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    level: int


class RoleAssign(BaseModel):
    role_names: list[str] = Field(min_length=1)


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    action: str
    method: str
    path: str
    status_code: int
    client_ip: str | None = None
    duration_ms: float
    request_id: str | None = None
    created_at: datetime


__all__ = ["AuditLogOut", "RoleAssign", "RoleOut", "UserCreate", "UserOut", "UserUpdate"]
