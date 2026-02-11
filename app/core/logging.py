import logging

from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    # Nivel global
    logging.getLogger().setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Silenciar ruido
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.db_echo else logging.WARNING
    )
