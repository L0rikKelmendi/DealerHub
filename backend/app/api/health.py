"""Liveness / readiness probes."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text

from app.core.cache import get_cache
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok", "service": "dealerhub-api"}


@router.get("/health/ready", summary="Readiness probe (DB + Redis)")
async def readiness(response: Response, db=Depends(get_db)) -> dict:
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        pass
    redis_ok = await get_cache().ping()
    status = "ready" if (db_ok and redis_ok) else "degraded"
    if status != "ready":
        response.status_code = 503
    return {
        "status": status,
        "components": {
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
    }
