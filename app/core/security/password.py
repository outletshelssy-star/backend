import bcrypt as _bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if _is_bcrypt(hashed):
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _is_bcrypt(hashed) or _ph.check_needs_rehash(hashed)


def _is_bcrypt(hashed: str) -> bool:
    return hashed.startswith(("$2b$", "$2a$", "$2y$"))
