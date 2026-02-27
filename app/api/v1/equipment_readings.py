from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.enums import EquipmentStatus, UserType
from app.models.equipment import Equipment
from app.models.equipment_inspection import EquipmentInspection
from app.models.equipment_reading import (
    EquipmentReading,
    EquipmentReadingCreate,
    EquipmentReadingListResponse,
    EquipmentReadingRead,
)
from app.models.equipment_type import EquipmentType
from app.models.user import User
from app.utils.measurements.temperature import Temperature

router = APIRouter(
    prefix="/equipment-readings",
    tags=["Equipment Readings"],
)


def _require_id(value: int | None, label: str) -> int:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{label} has no ID",
        )
    return value


def _normalize_temperature(value: float, unit: str) -> float:
    unit_key = unit.strip().lower()
    try:
        if unit_key in {"c", "celsius"}:
            return Temperature.from_celsius(value).as_celsius
        if unit_key in {"f", "fahrenheit"}:
            return Temperature.from_fahrenheit(value).as_celsius
        if unit_key in {"k", "kelvin"}:
            return Temperature.from_kelvin(value).as_celsius
        if unit_key in {"r", "rankine"}:
            return Temperature.from_rankine(value).as_celsius
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported temperature unit",
    )


def _get_inspection_days(equipment: Equipment, equipment_type: EquipmentType) -> int:
    if equipment.inspection_days_override is not None:
        return equipment.inspection_days_override
    return equipment_type.inspection_days


def _as_utc(dt_value: datetime) -> datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=UTC)
    return dt_value.astimezone(UTC)


@router.post(
    "/equipment/{equipment_id}",
    response_model=EquipmentReadingRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_400_BAD_REQUEST: {"description": "Solicitud inválida"},
    },
)
def create_equipment_reading(
    equipment_id: int,
    payload: EquipmentReadingCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentReadingRead:
    """
    Registra una lectura de equipo (temperatura) para un equipo.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 400: solicitud inválida.
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    if equipment.status == EquipmentStatus.needs_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Equipment needs review before recording readings",
        )
    if equipment.status != EquipmentStatus.in_use:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Equipment must be in_use to record readings",
        )
    equipment_type = session.get(EquipmentType, equipment.equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )

    value_celsius = _normalize_temperature(payload.value, payload.unit)
    measured_at = (
        _as_utc(payload.measured_at) if payload.measured_at else datetime.now(UTC)
    )

    inspection_days = _get_inspection_days(equipment, equipment_type)
    if inspection_days > 0:
        measured_date = measured_at.date()
        day_end = datetime(
            measured_date.year,
            measured_date.month,
            measured_date.day,
            tzinfo=UTC,
        ) + timedelta(days=1)
        last_inspection = session.exec(
            select(EquipmentInspection)
            .where(EquipmentInspection.equipment_id == equipment.id)
            .where(EquipmentInspection.inspected_at < day_end)
            .order_by(desc(EquipmentInspection.inspected_at))  # type: ignore[arg-type]
        ).first()
        if not last_inspection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inspection required before recording readings",
            )
        cutoff_date = measured_date - timedelta(days=inspection_days)
        inspected_date = _as_utc(last_inspection.inspected_at).date()
        if inspected_date < cutoff_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last inspection is older than allowed window",
            )

    equipment_db_id = _require_id(equipment.id, "Equipment")
    reading = EquipmentReading(
        equipment_id=equipment_db_id,
        value_celsius=value_celsius,
        measured_at=measured_at,
        created_by_user_id=current_user.id,
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return EquipmentReadingRead(**reading.model_dump())


@router.get(
    "/equipment/{equipment_id}",
    response_model=EquipmentReadingListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment_readings(
    equipment_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> Any:
    """
    Lista lecturas de un equipo.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    """
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    readings = session.exec(
        select(EquipmentReading)
        .where(EquipmentReading.equipment_id == equipment_id)
        .order_by(desc(EquipmentReading.measured_at))  # type: ignore[arg-type]
    ).all()
    if not readings:
        return EquipmentReadingListResponse(message="No records found")
    return EquipmentReadingListResponse(
        items=[EquipmentReadingRead(**r.model_dump()) for r in readings]
    )
