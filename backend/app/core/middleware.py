"""ASGI middleware: request logging (+AuditLog persistence) and the
authentication context middleware that resolves JWTs for every request.

The middlewares are intentionally independent of route handlers:

* ``RequestLoggingMiddleware`` assigns a request id, measures duration and
  emits one structured log line per request.  Mutating API calls are also
  persisted into the ``audit_logs`` table.
* ``AuthContextMiddleware`` best-effort decodes the bearer token and stores
  ``user_id`` / ``company_id`` on ``request.state`` so the logging middleware
  can attribute the action.  Actual authorization happens in the route
  dependencies (``app.core.deps``) — this middleware never blocks a request.
"""

import logging
import time
import uuid
from contextvars import ContextVar

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.audit import AuditLog

logger = logging.getLogger("dealerhub.request")

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Timing + structured logging + audit trail for mutating requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        request_id_ctx.set(request_id)

        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            user_id = getattr(request.state, "user_id", None)
            company_id = getattr(request.state, "company_id", None)
            response = response or None

            logger.info(
                "http_request",
                extra={
                    "props": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code if response else 500,
                        "duration_ms": duration_ms,
                        "client_ip": request.client.host if request.client else None,
                        "user_id": str(user_id) if user_id else None,
                        "company_id": str(company_id) if company_id else None,
                    }
                },
            )

            if (
                request.method in ("POST", "PUT", "PATCH", "DELETE")
                and request.url.path.startswith("/api")
                and response is not None
                and response.status_code < 500
            ):
                # prefer the request's own session (same transaction);
                # fall back to a fresh session for unauthenticated routes
                session = getattr(request.state, "db", None)
                fresh = session is None
                if fresh:
                    session = SessionLocal()
                try:
                    session.add(
                        AuditLog(
                            company_id=company_id,
                            user_id=user_id,
                            action=f"{request.method} {request.url.path}",
                            method=request.method,
                            path=request.url.path,
                            status_code=response.status_code,
                            client_ip=request.client.host if request.client else None,
                            duration_ms=duration_ms,
                            request_id=request_id,
                        )
                    )
                    await session.commit()
                except Exception:  # noqa: BLE001 - auditing must not break requests
                    logger.exception("failed to persist audit log")
                finally:
                    if fresh:
                        await session.close()

        return response  # type: ignore[return-value]


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Best-effort JWT resolution; enriches request.state for logging."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user_id = None
        request.state.company_id = None
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            try:
                payload = decode_token(token)
                if payload.get("type") == "access":
                    request.state.user_id = uuid.UUID(payload["sub"])
                    company = payload.get("company_id")
                    request.state.company_id = uuid.UUID(company) if company else None
            except (jwt.PyJWTError, ValueError, TypeError):
                pass  # invalid tokens are rejected by the route dependencies
        return await call_next(request)
