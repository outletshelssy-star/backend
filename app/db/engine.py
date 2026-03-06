from sqlmodel import create_engine

from app.core.config import get_settings

settings = get_settings()

if not settings.database_url:
    raise RuntimeError("DATABASE_URL is not set. Check your .env file.")

engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
)
