"""Tenant administration + role-based access tests (companies & branches)."""

import pytest

pytestmark = pytest.mark.asyncio


# --- companies ------------------------------------------------------------- #


async def test_company_admin_requires_superuser(api, owner_a):
    resp = await api.as_user(owner_a).get("/api/v1/companies")
    assert resp.status_code == 403


async def test_superuser_lists_companies(api, admin, company_a, company_b):
    resp = await api.as_user(admin).get("/api/v1/companies")
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()["items"]}
    assert {"Prishtina Motors", "Tirana Auto Group"} <= names


async def test_superuser_creates_company(api, admin):
    resp = await api.as_user(admin).post(
        "/api/v1/companies",
        json={
            "name": "Gjakova Cars",
            "slug": "gjakova-cars",
            "city": "Gjakova",
            "country": "Kosovo",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "gjakova-cars"


async def test_my_company_returns_tenant(api, owner_a, company_a):
    resp = await api.as_user(owner_a).get("/api/v1/companies/me")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Prishtina Motors"


async def test_company_update_isolated_per_tenant(api, owner_a, owner_b, company_b):
    """A user cannot modify another company even with the owner role."""
    resp = await api.as_user(owner_a).patch(
        f"/api/v1/companies/{company_b.id}", json={"name": "Hacked Co"}
    )
    assert resp.status_code == 403


async def test_owner_updates_own_company(api, owner_a, company_a):
    resp = await api.as_user(owner_a).patch(
        f"/api/v1/companies/{company_a.id}", json={"phone": "+383 44 111 222"}
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+383 44 111 222"


# --- branches --------------------------------------------------------------- #


async def test_create_and_list_branches(api, owner_a, company_a):
    resp = await api.as_user(owner_a).post(
        "/api/v1/branches",
        json={"name": "Dukagjini Branch", "code": "DUK", "city": "Peja"},
    )
    assert resp.status_code == 201, resp.text

    listing = await api.as_user(owner_a).get("/api/v1/branches")
    assert listing.status_code == 200
    assert any(b["code"] == "DUK" for b in listing.json()["items"])


async def test_branch_management_requires_role(api, viewer_a):
    resp = await api.as_user(viewer_a).post(
        "/api/v1/branches", json={"name": "Nope", "code": "NOP"}
    )
    assert resp.status_code == 403


async def test_salesperson_cannot_create_branch(api, sales_a):
    resp = await api.as_user(sales_a).post("/api/v1/branches", json={"name": "Nope", "code": "NOP"})
    assert resp.status_code == 403


async def test_branch_isolated_between_tenants(api, owner_a, owner_b, db, company_a):
    from tests.conftest import make_branch

    branch = await make_branch(db, company_a)
    resp = await api.as_user(owner_b).get(f"/api/v1/branches/{branch.id}")
    assert resp.status_code == 404
