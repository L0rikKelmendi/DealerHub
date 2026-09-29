"""Demo data seeder — run with: python -m app.seed"""

import asyncio

from sqlalchemy import select

from app.core.roles import ROLE_DESCRIPTIONS, ROLE_LEVELS
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.tenant import Branch, Company
from app.models.user import Role, User, UserRole

DEMO_PASSWORD = "Password123!"


async def seed() -> None:
    async with SessionLocal() as db:
        # 1. roles (global catalog)
        result = await db.execute(select(Role))
        if not result.scalars().first():
            for name, level in ROLE_LEVELS.items():
                db.add(Role(name=name, level=level, description=ROLE_DESCRIPTIONS[name]))
            await db.flush()

        result = await db.execute(select(User).where(User.email == "owner@prishtina.dev"))
        if result.scalar_one_or_none():
            print("demo data already present — skipping")
            return

        # 2. two tenant companies
        prishtina = Company(name="Prishtina Motors", slug="prishtina-motors", city="Prishtinë")
        tirana = Company(name="Tirana Auto Group", slug="tirana-auto-group", city="Tiranë")
        db.add_all([prishtina, tirana])
        await db.flush()

        branch1 = Branch(
            company_id=prishtina.id, name="Main Showroom", code="MAIN", city="Prishtinë"
        )
        branch2 = Branch(
            company_id=prishtina.id, name="Dukagjini Branch", code="DUK", city="Pejë"
        )
        db.add_all([branch1, branch2])

        roles = {r.name: r for r in (await db.execute(select(Role))).scalars().all()}

        async def user(email, name, company_id, role_name):
            u = User(
                company_id=company_id,
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=name,
            )
            db.add(u)
            await db.flush()
            db.add(UserRole(user_id=u.id, role_id=roles[role_name].id))
            return u

        await user("owner@prishtina.dev", "Ardit Krasniqi", prishtina.id, "owner")
        await user("sales@prishtina.dev", "Sara Shala", prishtina.id, "salesperson")
        await user("accountant@prishtina.dev", "Ana Berisha", prishtina.id, "accountant")
        await user("owner@tirana.dev", "Ben Meta", tirana.id, "owner")

        await db.commit()

    print("seeded: 2 companies, 2 branches, 4 demo users")
    print(f"demo login → owner@prishtina.dev / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
