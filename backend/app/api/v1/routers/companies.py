"""Platform-admin company management + per-tenant company info."""

from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, PageParams, SuperUser
from app.core.exceptions import PermissionDeniedError
from app.models.tenant import Company
from app.schemas.common import MessageOut, PageOut
from app.schemas.tenant import CompanyCreate, CompanyOut, CompanyUpdate
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get(
    "/me",
    response_model=CompanyOut,
    summary="Current user's company (tenant)",
)
async def my_company(user: CurrentUser, db: DbSession) -> CompanyOut:
    service = CompanyService(db, user.company_id)
    company = await service.repo.get_or_404(user.company_id)
    return CompanyOut.model_validate(company)


@router.get(
    "",
    response_model=PageOut[CompanyOut],
    summary="List all companies (platform admin only)",
)
async def list_companies(admin: SuperUser, db: DbSession, params: PageParams) -> dict:
    service = CompanyService(db, company_id=None)
    rows, page = await service.repo.paginate(select(Company), params)
    return {
        "items": [CompanyOut.model_validate(c).model_dump(mode="json") for c in rows],
        "page": page.model_dump(mode="json"),
    }


@router.post(
    "",
    response_model=CompanyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company (platform admin only)",
)
async def create_company(payload: CompanyCreate, admin: SuperUser, db: DbSession) -> CompanyOut:
    service = CompanyService(db, company_id=None)
    company = await service.create(payload)
    return CompanyOut.model_validate(company)


@router.get(
    "/{company_id}",
    response_model=CompanyOut,
    summary="Get one company (platform admin only)",
)
async def get_company(company_id: UUID, admin: SuperUser, db: DbSession) -> CompanyOut:
    service = CompanyService(db, company_id=None)
    return CompanyOut.model_validate(await service.repo.get_or_404(company_id))


@router.patch(
    "/{company_id}",
    response_model=CompanyOut,
    summary="Update a company (platform admin or the company's own users)",
)
async def update_company(
    company_id: UUID, payload: CompanyUpdate, user: CurrentUser, db: DbSession
) -> CompanyOut:
    if not user.is_superuser and user.company_id != company_id:
        raise PermissionDeniedError("cannot modify another company")
    service = CompanyService(db, company_id=None)
    company = await service.update(company_id, payload)
    return CompanyOut.model_validate(company)


@router.delete(
    "/{company_id}",
    response_model=MessageOut,
    status_code=status.HTTP_200_OK,
    summary="Deactivate a company (platform admin only)",
)
async def deactivate_company(company_id: UUID, admin: SuperUser, db: DbSession) -> MessageOut:
    service = CompanyService(db, company_id=None)
    await service.update(company_id, CompanyUpdate(is_active=False))
    return MessageOut(detail="company deactivated")
