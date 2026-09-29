"""Shared fixtures: isolated transactional DB, tenant factories, API client.

Environment is pointed at throwaway databases *before* the app is imported:

* TEST_DATABASE_URL (default postgres://…/dealerhub_test) — schema recreated
  once per session, every test wrapped in a rolled-back transaction
* TEST_REDIS_URL   (default redis://localhost:6380/1) — flushed per test
"""

import os

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://dealerhub:dealerhub@localhost:5433/dealerhub_test",
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/1")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.cache import get_cache
from app.core.roles import RoleName
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models.tenant import Branch, Company
from app.models.user import Role, User, UserRole

# --------------------------------------------------------------------------- #
# database
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """Transactional session: commits become savepoints, rolled back after."""
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(
        bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    yield session
    await session.close()
    await trans.rollback()
    await conn.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_cache():
    """Flush the test Redis DB before every test."""
    await get_cache().flush()
    yield


# --------------------------------------------------------------------------- #
# application + client
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def app(db):
    from fastapi import Request

    from app.main import app as fastapi_app

    async def override_get_db(request: Request):
        # mirror the production get_db contract: publish the session so the
        # audit middleware joins the same transaction
        request.state.db = db
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


def auth_headers(user: User) -> dict:
    token = create_access_token(
        str(user.id), str(user.company_id) if user.company_id else None, user.role_names
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def api(app, db):
    """Anonymous client + helper to switch identity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:

        def as_user(user: User) -> AsyncClient:
            c.headers.update(auth_headers(user))
            return c

        c.as_user = as_user  # type: ignore[attr-defined]
        yield c


# --------------------------------------------------------------------------- #
# tenant / identity factories
# --------------------------------------------------------------------------- #


async def _ensure_roles(db) -> dict[str, Role]:
    from sqlalchemy import select

    res = await db.execute(select(Role))
    existing = {r.name: r for r in res.scalars().all()}
    if existing:
        return existing
    roles = {}
    for name, level in [
        (RoleName.OWNER, 100),
        (RoleName.MANAGER, 80),
        (RoleName.SALESPERSON, 40),
        (RoleName.ACCOUNTANT, 30),
        (RoleName.SERVICE, 20),
        (RoleName.VIEWER, 10),
    ]:
        role = Role(name=name, level=level)
        db.add(role)
        roles[name] = role
    await db.flush()
    return roles


async def make_company(db, name: str = "Prishtina Motors", slug: str | None = None) -> Company:
    company = Company(
        name=name,
        slug=slug or f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
        city="Prishtinë",
        country="Kosovo",
    )
    db.add(company)
    await db.flush()
    return company


async def make_user(
    db,
    company: Company,
    email: str,
    full_name: str = "Test User",
    role: str = RoleName.OWNER,
    is_superuser: bool = False,
) -> User:
    roles = await _ensure_roles(db)
    user = User(
        company_id=company.id,
        email=email,
        hashed_password=hash_password("Password123!"),
        full_name=full_name,
        is_superuser=is_superuser,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=roles[role].id))
    await db.flush()

    # re-query so the selectin strategy eagerly loads roles for later
    # synchronous access (token creation in auth_headers)
    from sqlalchemy import select

    loaded = (await db.execute(select(User).where(User.email == email))).scalar_one()
    return loaded


async def make_branch(db, company: Company, name: str = "Main Showroom") -> Branch:
    branch = Branch(company_id=company.id, name=name, code=f"BR-{uuid.uuid4().hex[:4]}")
    db.add(branch)
    await db.flush()
    return branch


@pytest_asyncio.fixture
async def roles(db):
    return await _ensure_roles(db)


@pytest_asyncio.fixture
async def company_a(db) -> Company:
    return await make_company(db, "Prishtina Motors")


@pytest_asyncio.fixture
async def company_b(db) -> Company:
    return await make_company(db, "Tirana Auto Group")


@pytest_asyncio.fixture
async def owner_a(db, company_a) -> User:
    return await make_user(db, company_a, "owner.a@test.dev", "Ardit Owner", RoleName.OWNER)


@pytest_asyncio.fixture
async def manager_a(db, company_a) -> User:
    return await make_user(db, company_a, "manager.a@test.dev", "Mira Manager", RoleName.MANAGER)


@pytest_asyncio.fixture
async def sales_a(db, company_a) -> User:
    return await make_user(db, company_a, "sales.a@test.dev", "Sara Sales", RoleName.SALESPERSON)


@pytest_asyncio.fixture
async def accountant_a(db, company_a) -> User:
    return await make_user(
        db, company_a, "accountant.a@test.dev", "Ana Accountant", RoleName.ACCOUNTANT
    )


@pytest_asyncio.fixture
async def service_a(db, company_a) -> User:
    return await make_user(db, company_a, "service.a@test.dev", "Sam Service", RoleName.SERVICE)


@pytest_asyncio.fixture
async def viewer_a(db, company_a) -> User:
    return await make_user(db, company_a, "viewer.a@test.dev", "Vera Viewer", RoleName.VIEWER)


@pytest_asyncio.fixture
async def owner_b(db, company_b) -> User:
    return await make_user(db, company_b, "owner.b@test.dev", "Ben Owner", RoleName.OWNER)


@pytest_asyncio.fixture
async def admin(db) -> User:
    """Platform superuser without a company."""
    user = User(
        email="platform.admin@test.dev",
        hashed_password=hash_password("Password123!"),
        full_name="Platform Admin",
        is_superuser=True,
    )
    db.add(user)
    await db.flush()
    return user
