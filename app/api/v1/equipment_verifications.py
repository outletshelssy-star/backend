from fastapi import APIRouter

from app.api.v1 import equipment_verifications_commands, equipment_verifications_queries
from app.api.v1.equipment_verifications_shared import _parse_monthly_readings_from_notes

router = APIRouter(
    prefix="/equipment-verifications",
    tags=["Equipment Verifications"],
)
router.include_router(equipment_verifications_commands.router)
router.include_router(equipment_verifications_queries.router)

__all__ = ["router", "_parse_monthly_readings_from_notes"]
