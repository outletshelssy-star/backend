from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.security.password import hash_password
from app.models.enums import UserType
from app.models.user import User


def ensure_superadmin(session: Session) -> None:
    """
    Verifica si existe un superadmin.
    Si no existe, lo crea.
    """
    statement = select(User).where(User.user_type == UserType.superadmin)
    superadmin = session.exec(statement).first()

    if superadmin:
        return  # ✅ ya existe, no hacer nada

    settings = get_settings()

    password = settings.superadmin_password

    if not password:
        raise RuntimeError("SUPERADMIN_PASSWORD must be set to create superadmin")

    user = User(
        name=settings.superadmin_name,
        last_name=settings.superadmin_last_name,
        email=settings.superadmin_email,
        user_type=UserType.superadmin,
        password_hash=hash_password(password),
        is_active=True,
    )

    session.add(user)
    session.commit()
