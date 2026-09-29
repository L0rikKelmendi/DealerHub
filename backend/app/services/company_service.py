"""Company (tenant) administration service."""

import uuid

from sqlalchemy import select

from app.core.exceptions import ConflictError
from app.db.repository import BaseRepository
from app.models.tenant import Branch, Company
from app.schemas.tenant import CompanyCreate, CompanyUpdate
from app.services.base import BaseService


class CompanyRepository(BaseRepository[Company]):
    model = Company


class CompanyService(BaseService[Company]):
    repository_class = CompanyRepository

    async def create(self, payload: CompanyCreate) -> Company:
        result = await self.db.execute(select(Company).where(Company.slug == payload.slug))
        if result.scalar_one_or_none():
            raise ConflictError("company slug already exists")
        return await self.repo.create(**payload.model_dump())

    async def update(self, company_id: uuid.UUID, payload: CompanyUpdate) -> Company:
        company = await self.repo.get_or_404(company_id)
        return await self.repo.update(company, **payload.model_dump(exclude_unset=True))


class BranchRepository(BaseRepository[Branch]):
    model = Branch


class BranchService(BaseService[Branch]):
    repository_class = BranchRepository
