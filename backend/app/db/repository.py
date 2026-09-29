"""Generic repository implementing the tenant-scoped data-access layer.

Every business model carries a ``company_id`` foreign key; repositories
automatically append that predicate so a request from company A can never
read or mutate rows that belong to company B (multi-tenancy isolation).
"""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page, PaginationParams
from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base class with generic CRUD + tenant scoping + pagination."""

    model: type[ModelT]

    def __init__(self, db: AsyncSession, company_id: uuid.UUID | None = None):
        self.db = db
        self.company_id = company_id

    # ------------------------------------------------------------------ #
    # tenant scoping
    # ------------------------------------------------------------------ #
    def _scoped(self, stmt: Select) -> Select:
        """Append the tenant predicate when the repository is tenant-bound."""
        if self.company_id is not None and hasattr(self.model, "company_id"):
            stmt = stmt.where(self.model.company_id == self.company_id)
        return stmt

    # ------------------------------------------------------------------ #
    # reads
    # ------------------------------------------------------------------ #
    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        stmt = self._scoped(select(self.model).where(self.model.id == entity_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_404(self, entity_id: uuid.UUID) -> ModelT:
        from app.core.exceptions import NotFoundError

        obj = await self.get(entity_id)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} not found")
        return obj

    async def count(self, stmt: Select) -> int:
        stmt = self._scoped(stmt)
        subq = stmt.order_by(None).subquery()
        result = await self.db.execute(select(func.count()).select_from(subq))
        return int(result.scalar_one())

    async def paginate(self, stmt: Select, params: PaginationParams) -> tuple[list[ModelT], Page]:
        """Tenant-scoped pagination of an arbitrary select statement."""
        from app.core.pagination import paginate as run_paginate

        return await run_paginate(self.db, self._scoped(stmt), params)

    # ------------------------------------------------------------------ #
    # writes
    # ------------------------------------------------------------------ #
    async def create(self, **values: Any) -> ModelT:
        if self.company_id is not None and hasattr(self.model, "company_id"):
            values.setdefault("company_id", self.company_id)
        obj = self.model(**values)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def add(self, obj: ModelT) -> ModelT:
        """Add an already-constructed instance and commit."""
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelT, **values: Any) -> ModelT:
        for key, value in values.items():
            setattr(obj, key, value)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)
        await self.db.commit()

    async def delete_where(self, *conditions: Any) -> int:
        stmt = self._scoped(delete(self.model).where(*conditions))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return int(result.rowcount or 0)
