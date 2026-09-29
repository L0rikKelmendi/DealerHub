"""Audit log inspection (owner/manager)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, PageParams, require_roles
from app.core.roles import RoleName
from app.models.audit import AuditLog
from app.schemas.common import PageOut
from app.schemas.user import AuditLogOut

router = APIRouter(
    prefix="/audit-logs",
    tags=["audit"],
    dependencies=[Depends(require_roles(RoleName.OWNER, RoleName.MANAGER))],
)


@router.get("", response_model=PageOut[AuditLogOut], summary="List audit entries")
async def list_audit_logs(user: CurrentUser, db: DbSession, params: PageParams) -> dict:
    from app.core.pagination import paginate

    stmt = (
        select(AuditLog)
        .where(AuditLog.company_id == user.company_id)
        .order_by(AuditLog.created_at.desc())
    )
    rows, page = await paginate(db, stmt, params)
    return {
        "items": [AuditLogOut.model_validate(a).model_dump(mode="json") for a in rows],
        "page": page.model_dump(mode="json"),
    }
