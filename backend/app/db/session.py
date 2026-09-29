"""Async engine / session factory and the FastAPI dependency."""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session, rolling back on unhandled errors.

    The session is also published on ``request.state.db`` so middleware
    (audit logging) can join the *same* transaction as the request —
    an atomic audit trail instead of a second, separate write.
    """
    async with SessionLocal() as session:
        request.state.db = session
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
