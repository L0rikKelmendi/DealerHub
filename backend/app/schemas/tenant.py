"""Tenant (company / branch) schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    vat_number: str | None = Field(None, max_length=40)
    email: str | None = Field(None, max_length=160)
    phone: str | None = Field(None, max_length=40)
    address: str | None = Field(None, max_length=200)
    city: str | None = Field(None, max_length=80)
    country: str | None = Field(None, max_length=80)
    plan: str = "standard"
    is_active: bool = True


class CompanyCreate(CompanyBase):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")


class CompanyUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=160)
    vat_number: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    plan: str | None = None
    is_active: bool | None = None


class CompanyOut(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    created_at: datetime
    updated_at: datetime


class BranchBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=1, max_length=20)
    address: str | None = Field(None, max_length=200)
    city: str | None = Field(None, max_length=80)
    phone: str | None = None
    is_active: bool = True
    staff_capacity: int = 10


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    code: str | None = Field(None, min_length=1, max_length=20)
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    staff_capacity: int | None = Field(None, ge=1)


class BranchOut(BranchBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime
