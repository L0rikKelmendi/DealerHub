"""Middleware behaviour: logging + auth context + audit persistence."""

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog

pytestmark = pytest.mark.asyncio


async def _audit_rows(db, company_id):
    """Audit rows are written via the request session — read through the
    same test session so in-transaction rows are visible."""
    result = await db.execute(select(AuditLog).where(AuditLog.company_id == company_id))
    return result.scalars().all()


async def test_mutating_request_creates_audit_entry(api, db, owner_a, company_a):
    resp = await api.as_user(owner_a).post(
        "/api/v1/branches", json={"name": "Audited Branch", "code": "AUD"}
    )
    assert resp.status_code == 201

    rows = await _audit_rows(db, company_a.id)
    assert any(
        r.method == "POST" and r.path == "/api/v1/branches" and r.status_code == 201 for r in rows
    )


async def test_get_requests_are_not_audited(api, db, owner_a, company_a):
    await api.as_user(owner_a).get("/api/v1/branches")
    rows = await _audit_rows(db, company_a.id)
    assert all(r.method != "GET" for r in rows)


async def test_audit_attributes_actor_company_and_request_id(api, db, owner_a, company_a):
    await api.as_user(owner_a).post("/api/v1/branches", json={"name": "X Branch", "code": "XB"})
    rows = [r for r in await _audit_rows(db, company_a.id) if r.path == "/api/v1/branches"]
    assert rows, "no audit row written"
    row = rows[-1]
    assert row.user_id == owner_a.id
    assert row.company_id == company_a.id
    assert row.request_id is not None
    assert row.duration_ms >= 0


async def test_audit_endpoint_returns_entries(api, db, owner_a, company_a):
    await api.as_user(owner_a).post(
        "/api/v1/branches", json={"name": "Listed Branch", "code": "LB"}
    )
    resp = await api.as_user(owner_a).get("/api/v1/audit-logs")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert items[0]["action"].startswith("POST")


async def test_audit_requires_role(api, sales_a):
    resp = await api.as_user(sales_a).get("/api/v1/audit-logs")
    assert resp.status_code == 403
