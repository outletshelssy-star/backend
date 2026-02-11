from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt

from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def create_access_token(
    subject: str | int,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),
        "ver": token_version,
        "exp": expire,
    }

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
