"""Identity & access models: User, Role, UserRole, RefreshToken."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An employee of a company (tenant) or a platform administrator."""

    __tablename__ = "users"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(120), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company = relationship("Company", back_populates="users")
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles", lazy="selectin", viewonly=True
    )

    @property
    def role_names(self) -> list[str]:
        """Roles of this user; empty when not yet loaded (avoids lazy IO)."""
        from sqlalchemy import inspect as sa_inspect

        if "roles" in sa_inspect(self).unloaded:
            return []
        return sorted(r.name for r in self.roles)


class UserRole(Base):
    """Association table binding users to roles within their company."""

    __tablename__ = "user_roles"

    # the composite primary key already guarantees pair uniqueness
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A role (owner, manager, salesperson, accountant, service, viewer)."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))
    level: Mapped[int] = mapped_column(default=0)

    users: Mapped[list[User]] = relationship(secondary="user_roles", viewonly=True)


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    """Server-side record of issued refresh tokens (hashed)."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(200))
    ip_address: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    user = relationship("User")
