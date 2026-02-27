import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.core.bootstrap.company import ensure_default_company
from app.core.bootstrap.equipment import ensure_default_equipment
from app.core.bootstrap.equipment_type import (
    ensure_default_equipment_type_inspection_items,
    ensure_default_equipment_type_verifications,
    ensure_default_equipment_types,
)
from app.core.bootstrap.external_analysis import ensure_default_external_analysis_types
from app.core.bootstrap.superadmin import ensure_superadmin
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db import events  # noqa: F401
from app.db.engine import engine

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()

    logger.info("🚀 Starting application")
    logger.info("Environment: %s", settings.app_env)

    if settings.app_env != "test":
        try:
            with Session(engine) as session:
                ensure_superadmin(session)
                ensure_default_company(session)
                if settings.app_env == "development":
                    ensure_default_equipment_types(session)
                    ensure_default_equipment_type_verifications(session)
                    ensure_default_equipment_type_inspection_items(session)
                    ensure_default_equipment(session)
                    ensure_default_external_analysis_types(session)
            logger.info("✅ Superadmin check completed")
        except Exception as err:
            logger.exception("❌ Failed to ensure superadmin")
            raise RuntimeError("Superadmin bootstrap failed") from err

    yield

    logger.info("🛑 Shutting down application")
