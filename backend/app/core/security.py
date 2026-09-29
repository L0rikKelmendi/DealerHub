"""Password hashing (bcrypt) and JWT creation / verification."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# --- passwords ----------------------------------------------------------- #


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# --- refresh tokens ------------------------------------------------------ #


def new_refresh_token() -> str:
    """Opaque refresh token: 256 bits of entropy, url-safe."""
    return uuid.uuid4().hex + uuid.uuid4().hex


def hash_token(token: str) -> str:
    """Refresh tokens are stored hashed so a DB leak cannot replay them."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --- JWT ------------------------------------------------------------------ #


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.JWT_ISSUER,
        "jti": uuid.uuid4().hex,  # unique even within the same second
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    user_id: str, company_id: str | None = None, roles: list[str] | None = None
) -> str:
    return _create_token(
        subject=user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"company_id": company_id, "roles": roles or []},
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT; raises jwt.PyJWTError on any problem."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        issuer=settings.JWT_ISSUER,
        options={"require": ["exp", "sub", "type"]},
    )
