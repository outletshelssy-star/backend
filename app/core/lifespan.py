import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.bootstrap import ensure_superadmin_account
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db import events  # noqa: F401

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()

    logger.info("🚀 Starting application")
    logger.info("Environment: %s", settings.app_env)

    if settings.app_env != "test":
        try:
            ensure_superadmin_account(app_env=settings.app_env)
            logger.info("✅ Superadmin check completed")
        except Exception as err:
            logger.exception("❌ Failed to ensure superadmin account")
            raise RuntimeError("Superadmin bootstrap failed") from err

    yield

    logger.info("🛑 Shutting down application")
