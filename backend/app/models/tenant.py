"""Tenant models: Company (the tenant root) and its Branches."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A dealership company — the tenant every business row hangs off."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    vat_number: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(80))
    country: Mapped[str | None] = mapped_column(String(80), default="Kosovo")
    plan: Mapped[str] = mapped_column(String(20), default="standard")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    branches: Mapped[list["Branch"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="company"
    )


class Branch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical dealership location belonging to a company."""

    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_branch_code"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    staff_capacity: Mapped[int] = mapped_column(Integer, default=10)

    company: Mapped[Company] = relationship(back_populates="branches")
