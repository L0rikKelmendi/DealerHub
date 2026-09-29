"""User administration + role assignment tests."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_user_with_roles(api, owner_a, company_a):
    resp = await api.as_user(owner_a).post(
        "/api/v1/users",
        json={
            "email": "new.sales@prishtina.dev",
            "password": "Password123!",
            "full_name": "New Salesperson",
            "role_names": ["salesperson"],
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role_names"] == ["salesperson"]


async def test_list_users_scoped_to_company(api, owner_a, company_a, company_b, owner_b, db):
    from tests.conftest import make_user

    await make_user(db, company_b, "b-only@tirana.dev", role="viewer")
    resp = await api.as_user(owner_a).get("/api/v1/users")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()["items"]]
    assert "b-only@tirana.dev" not in emails


async def test_user_admin_requires_owner_or_manager(api, sales_a):
    resp = await api.as_user(sales_a).get("/api/v1/users")
    assert resp.status_code == 403


async def test_replace_user_roles(api, owner_a, viewer_a):
    resp = await api.as_user(owner_a).post(
        f"/api/v1/users/{viewer_a.id}/roles",
        json={"role_names": ["manager", "accountant"]},
    )
    assert resp.status_code == 200
    assert sorted(resp.json()["role_names"]) == ["accountant", "manager"]


async def test_unknown_role_rejected(api, owner_a, viewer_a):
    resp = await api.as_user(owner_a).post(
        f"/api/v1/users/{viewer_a.id}/roles", json={"role_names": ["wizard"]}
    )
    assert resp.status_code == 404


async def test_cannot_deactivate_self(api, owner_a):
    resp = await api.as_user(owner_a).delete(f"/api/v1/users/{owner_a.id}")
    assert resp.status_code == 409


async def test_deactivate_user(api, owner_a, sales_a):
    resp = await api.as_user(owner_a).delete(f"/api/v1/users/{sales_a.id}")
    assert resp.status_code == 200
    resp2 = await api.as_user(owner_a).get(f"/api/v1/users/{sales_a.id}")
    assert resp2.json()["is_active"] is False


async def test_roles_catalog(api, owner_a):
    resp = await api.as_user(owner_a).get("/api/v1/roles")
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert {"owner", "manager", "salesperson", "accountant", "service", "viewer"} == names
