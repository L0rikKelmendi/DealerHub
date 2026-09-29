"""Authentication + registration + token lifecycle tests."""

import pytest

from app.core.security import decode_token

pytestmark = pytest.mark.asyncio

REGISTER = {
    "company_name": "Peja Premium Cars",
    "company_slug": "peja-premium",
    "full_name": "Leart Krasniqi",
    "email": "leart@peja.dev",
    "password": "SuperSecret123",
    "city": "Peja",
}


async def test_register_creates_company_and_owner(client, db):
    resp = await client.post("/api/v1/auth/register", json=REGISTER)
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["email"] == REGISTER["email"]
    assert user["role_names"] == ["owner"]
    assert user["company_id"] is not None


async def test_register_rejects_duplicate_email(client, db):
    await client.post("/api/v1/auth/register", json=REGISTER)
    second = {**REGISTER, "company_slug": "peja-premium-2", "email": "x@y.dev"}
    resp = await client.post("/api/v1/auth/register", json=second)
    # slug free but email duplicate → conflict
    third = {**REGISTER, "company_slug": "another-slug"}
    resp = await client.post("/api/v1/auth/register", json=third)
    assert resp.status_code == 409


async def test_register_rejects_duplicate_slug(client, db):
    await client.post("/api/v1/auth/register", json=REGISTER)
    dup = {**REGISTER, "email": "other@peja.dev"}
    resp = await client.post("/api/v1/auth/register", json=dup)
    assert resp.status_code == 409
    assert "slug" in resp.json()["message"].lower()


async def test_register_validates_password(client):
    bad = {**REGISTER, "password": "short"}
    resp = await client.post("/api/v1/auth/register", json=bad)
    assert resp.status_code == 422


async def test_login_returns_token_pair(client, db):
    await client.post("/api/v1/auth/register", json=REGISTER)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == REGISTER["email"]
    payload = decode_token(body["access_token"])
    assert payload["type"] == "access"
    assert payload["roles"] == ["owner"]


async def test_login_wrong_password(client, db):
    await client.post("/api/v1/auth/register", json=REGISTER)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": "WrongPassword1"},
    )
    assert resp.status_code == 401


async def test_me_requires_authentication(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(api, owner_a):
    resp = await api.as_user(owner_a).get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == owner_a.email


async def test_refresh_rotates_tokens(client, db):
    await client.post("/api/v1/auth/register", json=REGISTER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    tokens = login.json()

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    new_tokens = refresh.json()
    assert new_tokens["access_token"] != tokens["access_token"]

    # old refresh token is revoked after rotation
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert replay.status_code == 401


async def test_logout_revokes_refresh_token(client, db):
    await client.post("/api/v1/auth/register", json=REGISTER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    refresh_token = login.json()["refresh_token"]

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert out.status_code == 200

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401


async def test_change_password(api, owner_a):
    client = api.as_user(owner_a)
    resp = await client.post(
        "/api/v1/auth/me/password",
        json={"current_password": "Password123!", "new_password": "NewPassword456!"},
    )
    assert resp.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": owner_a.email, "password": "NewPassword456!"},
    )
    assert login.status_code == 200


async def test_invalid_token_rejected(api, owner_a):
    api.headers.update({"Authorization": "Bearer not-a-jwt"})
    resp = await api.get("/api/v1/auth/me")
    assert resp.status_code == 401
