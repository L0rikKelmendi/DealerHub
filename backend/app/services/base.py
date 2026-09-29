"""Service base class binding a repository to a tenant context."""

import uuid
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.repository import BaseRepository

ModelT = TypeVar("ModelT", bound=Base)


class BaseService(Generic[ModelT]):
    """Domain service operating on one tenant's data.

    Every service is constructed with the caller's ``company_id`` which it
    forwards to its repository — this is the single point where
    multi-tenant isolation enters the business layer.
    """

    repository_class: type[BaseRepository] = BaseRepository

    def __init__(self, db: AsyncSession, company_id: uuid.UUID | None):
        self.db = db
        self.company_id = company_id
        self.repo: BaseRepository = self.repository_class(db, company_id)

    # convenience passthroughs ------------------------------------------- #
    async def get(self, entity_id: uuid.UUID) -> ModelT:
        return await self.repo.get_or_404(entity_id)  # type: ignore[return-value]

    async def delete(self, entity_id: uuid.UUID) -> None:
        obj = await self.repo.get_or_404(entity_id)
        await self.repo.delete(obj)
