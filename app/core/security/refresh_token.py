import secrets

from app.core.security.password import hash_password, verify_password


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hash_password(token)


def verify_refresh_token(token: str, token_hash: str) -> bool:
    return verify_password(token, token_hash)
