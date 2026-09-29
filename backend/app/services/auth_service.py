"""Authentication: registration (company + owner), login, token refresh."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.roles import ROLE_DESCRIPTIONS, ROLE_LEVELS, RoleName
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.db.repository import BaseRepository
from app.models.tenant import Company
from app.models.user import RefreshToken, Role, User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:
    """Handles the full authentication lifecycle."""

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------ #
    async def ensure_system_roles(self, company_id: uuid.UUID) -> dict[str, Role]:
        """Create the six default roles for a freshly registered company."""
        result = await self.db.execute(select(Role))
        existing = {r.name: r for r in result.scalars().all()}
        roles: dict[str, Role] = {}
        for name, level in ROLE_LEVELS.items():
            role = existing.get(name)
            if role is None:
                role = Role(
                    name=name,
                    level=level,
                    description=ROLE_DESCRIPTIONS[name],
                )
                self.db.add(role)
            roles[name] = role
        await self.db.flush()
        return roles

    # ------------------------------------------------------------------ #
    async def register(self, payload: RegisterRequest) -> User:
        """Create a new tenant: company + owner user with the OWNER role."""
        dup = await self.db.execute(select(User).where(User.email == payload.email))
        if dup.scalar_one_or_none():
            raise ConflictError("an account with this e-mail already exists")
        dup_c = await self.db.execute(select(Company).where(Company.slug == payload.company_slug))
        if dup_c.scalar_one_or_none():
            raise ConflictError("company slug is already taken")

        company = Company(
            name=payload.company_name,
            slug=payload.company_slug,
            email=payload.email,
            phone=payload.phone,
            city=payload.city,
            country=payload.country,
        )
        self.db.add(company)
        await self.db.flush()

        roles = await self.ensure_system_roles(company.id)

        user = User(
            company_id=company.id,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
        )
        self.db.add(user)
        await self.db.flush()
        self.db.add(UserRole(user_id=user.id, role_id=roles[RoleName.OWNER].id))
        await self.db.commit()
        # re-query so the response reflects the loaded roles relationship
        refreshed = (await self.db.execute(select(User).where(User.id == user.id))).scalar_one()
        return refreshed

    # ------------------------------------------------------------------ #
    async def login(
        self, payload: LoginRequest, user_agent: str | None, ip: str | None
    ) -> tuple[User, str, str, int]:
        """Verify credentials and issue an access + refresh token pair."""
        result = await self.db.execute(select(User).where(User.email == payload.email).limit(1))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise AuthenticationError("invalid e-mail or password")
        if not user.is_active:
            raise PermissionDeniedError("account is disabled")

        user.last_login_at = datetime.now(UTC)

        refresh_raw = new_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh_raw),
                expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                user_agent=user_agent,
                ip_address=ip,
            )
        )
        await self.db.commit()
        await self.db.refresh(user)

        access = create_access_token(
            str(user.id), str(user.company_id) if user.company_id else None, user.role_names
        )
        return user, access, refresh_raw, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # ------------------------------------------------------------------ #
    async def refresh(self, refresh_raw: str) -> tuple[User, str, str, int]:
        """Rotate a refresh token: revoke old, issue a new pair."""
        token_hash = hash_token(refresh_raw)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if stored is None:
            raise AuthenticationError("unknown refresh token")
        if stored.revoked_at is not None:
            raise AuthenticationError("refresh token has been revoked")
        if stored.expires_at < now:
            raise AuthenticationError("refresh token expired")

        user = await self.db.get(User, stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("user not found or inactive")

        stored.revoked_at = now
        new_raw = new_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(new_raw),
                expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        await self.db.commit()

        access = create_access_token(
            str(user.id), str(user.company_id) if user.company_id else None, user.role_names
        )
        return user, access, new_raw, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # ------------------------------------------------------------------ #
    async def logout(self, refresh_raw: str) -> None:
        token_hash = hash_token(refresh_raw)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored is None:
            raise NotFoundError("refresh token not found")
        stored.revoked_at = datetime.now(UTC)
        await self.db.commit()

    # ------------------------------------------------------------------ #
    async def change_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.hashed_password):
            raise AuthenticationError("current password is incorrect")
        user.hashed_password = hash_password(new)
        await self.db.commit()

    # ------------------------------------------------------------------ #
    async def assign_roles(self, user: User, role_names: list[str]) -> User:
        """Replace a user's roles (admin operation)."""
        result = await self.db.execute(select(Role))
        by_name = {r.name: r for r in result.scalars().all()}
        unknown = [r for r in role_names if r not in by_name]
        if unknown:
            raise NotFoundError("unknown roles: " + ", ".join(unknown))

        await self.db.execute(UserRole.__table__.delete().where(UserRole.user_id == user.id))
        for name in role_names:
            self.db.add(UserRole(user_id=user.id, role_id=by_name[name].id))
        await self.db.commit()
        # the identity map still holds the pre-edit roles collection — expire it
        # so the re-query below repopulates the relationship
        self.db.expire(user, ["roles"])
        refreshed = (await self.db.execute(select(User).where(User.id == user.id))).scalar_one()
        return refreshed


class UserRepository(BaseRepository[User]):
    """User queries; users are global identities (email is unique)."""

    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_for_company(self, company_id: uuid.UUID) -> list[User]:
        result = await self.db.execute(select(User).where(User.company_id == company_id))
        return list(result.scalars().all())
