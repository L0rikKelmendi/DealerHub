"""User administration inside a tenant."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, PageParams, require_roles
from app.core.exceptions import ConflictError, NotFoundError
from app.core.roles import RoleName
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.common import PageOut
from app.schemas.user import RoleAssign, UserCreate, UserUpdate
from app.services.auth_service import AuthService, UserRepository

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_roles(RoleName.OWNER, RoleName.MANAGER))],
)


@router.get("", response_model=PageOut[UserOut], summary="List company users")
async def list_users(user: CurrentUser, db: DbSession, params: PageParams) -> dict:
    repo = UserRepository(db)
    rows, page = await repo.paginate(
        select(User).where(User.company_id == user.company_id).order_by(User.created_at.desc()),
        params,
    )
    return {
        "items": [UserOut.model_validate(u).model_dump(mode="json") for u in rows],
        "page": page.model_dump(mode="json"),
    }


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company user with roles (owner/manager)",
)
async def create_user(payload: UserCreate, user: CurrentUser, db: DbSession) -> UserOut:
    """Create an employee account in the caller's tenant with given roles."""
    service = AuthService(db)
    repo = UserRepository(db)
    if await repo.get_by_email(payload.email):
        raise ConflictError("an account with this e-mail already exists")
    if user.company_id is None:  # pragma: no cover - platform admins use /companies
        raise NotFoundError("caller has no company")

    new_user = User(
        company_id=user.company_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
    )
    db.add(new_user)
    await db.flush()
    new_user = await service.assign_roles(new_user, payload.role_names)
    return UserOut.model_validate(new_user)


@router.get("/{user_id}", response_model=UserOut, summary="Get one company user")
async def get_user(user_id: UUID, user: CurrentUser, db: DbSession) -> UserOut:
    target = await db.get(User, user_id)
    if target is None or target.company_id != user.company_id:
        raise NotFoundError("user not found")
    return UserOut.model_validate(target)


@router.patch("/{user_id}", response_model=UserOut, summary="Update user / roles")
async def update_user(
    user_id: UUID, payload: UserUpdate, user: CurrentUser, db: DbSession
) -> UserOut:
    service = AuthService(db)
    target = await db.get(User, user_id)
    if target is None or target.company_id != user.company_id:
        raise NotFoundError("user not found")

    values = payload.model_dump(exclude_unset=True)
    role_names = values.pop("role_names", None)
    if values:
        target = await UserRepository(db).update(target, **values)
    if role_names is not None:
        target = await service.assign_roles(target, role_names)
    return UserOut.model_validate(target)


@router.delete("/{user_id}", response_model=dict, summary="Deactivate a user")
async def deactivate_user(user_id: UUID, user: CurrentUser, db: DbSession) -> dict:
    target = await db.get(User, user_id)
    if target is None or target.company_id != user.company_id:
        raise NotFoundError("user not found")
    if target.id == user.id:
        raise ConflictError("cannot deactivate yourself")
    await UserRepository(db).update(target, is_active=False)
    return {"detail": "user deactivated"}


@router.post(
    "/{user_id}/roles",
    response_model=UserOut,
    summary="Replace a user's roles (owner/manager)",
)
async def assign_roles(
    user_id: UUID, payload: RoleAssign, user: CurrentUser, db: DbSession
) -> UserOut:
    service = AuthService(db)
    target = await db.get(User, user_id)
    if target is None or target.company_id != user.company_id:
        raise NotFoundError("user not found")
    target = await service.assign_roles(target, payload.role_names)
    return UserOut.model_validate(target)
