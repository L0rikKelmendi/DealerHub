"""Offset pagination contract shared by every list endpoint."""

import math

from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="1-based page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Rows per page")
    sort: str | None = Field(default=None, description="sort spec, e.g. -price,year")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel):
    """Generic paginated envelope."""

    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def meta(cls, total: int, params: PaginationParams) -> "Page":
        return cls(
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=max(1, math.ceil(total / params.page_size)) if total else 0,
        )


async def paginate(db: AsyncSession, stmt: Select, params: PaginationParams) -> tuple[list, Page]:
    """Execute ``stmt`` with limit/offset and return (rows, page metadata)."""
    count_subq = stmt.order_by(None).subquery()
    total = (await db.execute(select(func.count()).select_from(count_subq))).scalar_one()

    rows = (
        (await db.execute(stmt.offset(params.offset).limit(params.page_size)))
        .scalars()
        .unique()
        .all()
    )
    return list(rows), Page.meta(int(total), params)
