"""Authentication endpoints: register, login, refresh, logout, profile."""

from fastapi import APIRouter, Request, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.schemas.common import MessageOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new company (tenant) with its owner user",
    description=(
        "Creates a new company and its owner account. The owner receives "
        "the `owner` role and can then invite further users."
    ),
)
async def register(payload: RegisterRequest, db: DbSession) -> UserOut:
    service = AuthService(db)
    user = await service.register(payload)
    return UserOut.model_validate(user)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login with e-mail + password",
)
async def login(payload: LoginRequest, db: DbSession, request: Request) -> TokenPair:
    service = AuthService(db)
    user, access, refresh, expires_in = await service.login(
        payload,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Exchange a refresh token for a new token pair",
)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    service = AuthService(db)
    user, access, refresh_raw, expires_in = await service.refresh(payload.refresh_token)
    return TokenPair(
        access_token=access,
        refresh_token=refresh_raw,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageOut,
    summary="Revoke a refresh token",
)
async def logout(payload: RefreshRequest, db: DbSession) -> MessageOut:
    service = AuthService(db)
    await service.logout(payload.refresh_token)
    return MessageOut(detail="logged out")


@router.get("/me", response_model=UserOut, summary="Current user profile")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post(
    "/me/password",
    response_model=MessageOut,
    summary="Change own password",
)
async def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> MessageOut:
    service = AuthService(db)
    await service.change_password(user, payload.current_password, payload.new_password)
    return MessageOut(detail="password updated")
