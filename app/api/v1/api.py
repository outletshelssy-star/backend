"""Router principal de la API v1."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    companies,
    company_blocks,
    company_terminals,
    equipment,
    equipment_calibrations,
    equipment_inspections,
    equipment_readings,
    equipment_type,
    equipment_type_inspection_items,
    equipment_type_verification_items,
    equipment_type_verifications,
    equipment_verifications,
    external_analyses,
    hydrometer,
    samples,
    users,
)

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(company_blocks.router)
api_router.include_router(company_terminals.router)
api_router.include_router(equipment.router)
api_router.include_router(equipment_type.router)
api_router.include_router(equipment_type_inspection_items.router)
api_router.include_router(equipment_type_verifications.router)
api_router.include_router(equipment_type_verification_items.router)
api_router.include_router(external_analyses.router)
api_router.include_router(equipment_inspections.router)
api_router.include_router(equipment_verifications.router)
api_router.include_router(equipment_calibrations.router)
api_router.include_router(equipment_readings.router)
api_router.include_router(hydrometer.router)
api_router.include_router(samples.router)
