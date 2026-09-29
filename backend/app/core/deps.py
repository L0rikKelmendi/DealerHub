"""Reusable FastAPI dependencies: DB session, current user, role guards."""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.pagination import PaginationParams
from app.core.roles import RoleName
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Resolve the bearer token into an active ``User`` (raises 401)."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("not authenticated")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("invalid or expired token") from exc
    if payload.get("type") != "access":
        raise AuthenticationError("wrong token type")

    result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise AuthenticationError("user not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*role_names: str):
    """Dependency factory enforcing role-based authorization.

    A user holding the OWNER role always passes.
    """

    async def guard(user: CurrentUser) -> User:
        if RoleName.OWNER in user.role_names:
            return user
        if not set(role_names) & set(user.role_names):
            raise PermissionDeniedError("requires one of roles: " + ", ".join(role_names))
        return user

    return guard


async def require_superuser(user: CurrentUser) -> User:
    """Platform-level admin (manages the companies/tenants themselves)."""
    if not user.is_superuser:
        raise PermissionDeniedError("platform administrator privileges required")
    return user


SuperUser = Annotated[User, Depends(require_superuser)]


def pagination_params(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, description="e.g. -price,created_at"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size, sort=sort)


PageParams = Annotated[PaginationParams, Depends(pagination_params)]
