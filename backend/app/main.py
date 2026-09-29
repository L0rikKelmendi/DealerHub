"""DealerHub API application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.v1 import api_router
from app.core.cache import get_cache
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler
from app.core.logging_config import configure_logging
from app.core.middleware import (
    AuthContextMiddleware,
    RequestLoggingMiddleware,
)

logger = logging.getLogger("dealerhub")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.LOG_LEVEL)
    cache = get_cache()
    if await cache.ping():
        logger.info("redis cache connected")
    else:
        logger.warning("redis unavailable — running without caching")
    yield
    await cache.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Multi-company car dealership management platform.\n\n"
            "* REST API consumed by an independent React + TypeScript SPA\n"
            "* JWT auth with role-based authorization (owner/manager/salesperson/"
            "accountant/service/viewer)\n"
            "* Multi-tenant: every query is scoped to the caller's company\n"
            "* Redis caching, background worker (arq), OpenAI integration\n\n"
            "Authenticate via `/api/v1/auth/login` and use the **Authorize** button."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # order matters: auth context first enriches request.state,
    # the logging middleware wraps everything (incl. audit persistence)
    app.add_middleware(AuthContextMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # health probes live at the root (no auth, useful for load balancers)
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

    return app


app = create_app()
