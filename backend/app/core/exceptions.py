"""Domain exceptions translated to HTTP responses in ``app.main``."""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for domain errors with an attached HTTP status."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "internal_error"

    def __init__(self, message: str = "", details: dict | None = None):
        self.message = message or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "validation_error"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthenticated"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Translate domain exceptions into a uniform JSON error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )
