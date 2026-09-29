"""Branch management (per tenant)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, PageParams, require_roles
from app.core.roles import RoleName
from app.models.tenant import Branch
from app.models.user import User
from app.schemas.common import MessageOut, PageOut
from app.schemas.tenant import BranchCreate, BranchOut, BranchUpdate
from app.services.company_service import BranchService

router = APIRouter(prefix="/branches", tags=["branches"])

ManageGuard = Depends(require_roles(RoleName.OWNER, RoleName.MANAGER))


@router.get("", response_model=PageOut[BranchOut], summary="List branches")
async def list_branches(user: CurrentUser, db: DbSession, params: PageParams) -> dict:
    service = BranchService(db, user.company_id)
    rows, page = await service.repo.paginate(
        select(Branch).order_by(Branch.created_at.desc()), params
    )
    return {
        "items": [BranchOut.model_validate(b).model_dump(mode="json") for b in rows],
        "page": page.model_dump(mode="json"),
    }


@router.post(
    "",
    response_model=BranchOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a branch (owner/manager)",
)
async def create_branch(
    payload: BranchCreate,
    user: Annotated[User, ManageGuard],
    db: DbSession,
) -> BranchOut:
    service = BranchService(db, user.company_id)
    branch = await service.repo.create(**payload.model_dump())
    return BranchOut.model_validate(branch)


@router.get("/{branch_id}", response_model=BranchOut, summary="Get a branch")
async def get_branch(branch_id: UUID, user: CurrentUser, db: DbSession) -> BranchOut:
    service = BranchService(db, user.company_id)
    return BranchOut.model_validate(await service.repo.get_or_404(branch_id))


@router.patch(
    "/{branch_id}",
    response_model=BranchOut,
    summary="Update a branch (owner/manager)",
)
async def update_branch(
    branch_id: UUID,
    payload: BranchUpdate,
    user: Annotated[User, ManageGuard],
    db: DbSession,
) -> BranchOut:
    service = BranchService(db, user.company_id)
    branch = await service.repo.get_or_404(branch_id)
    branch = await service.repo.update(branch, **payload.model_dump(exclude_unset=True))
    return BranchOut.model_validate(branch)


@router.delete(
    "/{branch_id}",
    response_model=MessageOut,
    summary="Delete a branch (owner/manager)",
)
async def delete_branch(
    branch_id: UUID,
    user: Annotated[User, ManageGuard],
    db: DbSession,
) -> MessageOut:
    service = BranchService(db, user.company_id)
    await service.delete(branch_id)
    return MessageOut(detail="branch deleted")
