from sqlmodel import create_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url or "sqlite:///database.db",
    echo=settings.db_echo,
)
