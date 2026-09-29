"""Role catalog endpoints."""

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.user import Role
from app.schemas.user import RoleOut

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleOut], summary="List available roles")
async def list_roles(user: CurrentUser, db: DbSession) -> list[RoleOut]:
    result = await db.execute(select(Role).order_by(Role.level.desc()))
    return [RoleOut.model_validate(r) for r in result.scalars().all()]
