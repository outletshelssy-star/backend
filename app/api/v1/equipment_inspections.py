from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlmodel import Session, delete, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.enums import EquipmentStatus, InspectionResponseType, UserType
from app.models.equipment import Equipment
from app.models.equipment_calibration import EquipmentCalibration
from app.models.equipment_inspection import (
    EquipmentInspection,
    EquipmentInspectionCreate,
    EquipmentInspectionListResponse,
    EquipmentInspectionRead,
    EquipmentInspectionResponse,
    EquipmentInspectionResponseCreate,
    EquipmentInspectionResponseRead,
    EquipmentInspectionUpdate,
)
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_inspection_item import (
    EquipmentTypeInspectionItem,
)
from app.models.user import User
from app.models.user_terminal import UserTerminal

router = APIRouter(
    prefix="/equipment-inspections",
    tags=["Equipment Inspections"],
)


def _require_id(value: int | None, label: str) -> int:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{label} has no ID",
        )
    return value


def _validate_response(
    response_type: InspectionResponseType,
    value_bool: bool | None,
    value_text: str | None,
    value_number: float | None,
) -> None:
    if response_type == InspectionResponseType.boolean:
        if value_bool is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="value_bool is required for boolean responses",
            )
    elif response_type == InspectionResponseType.text:
        if not value_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="value_text is required for text responses",
            )
    elif response_type == InspectionResponseType.number:
        if value_number is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="value_number is required for number responses",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported response type",
        )


def _normalize_text(value: str) -> str:
    return value.strip().lower()


def _evaluate_response(
    item: EquipmentTypeInspectionItem,
    response: EquipmentInspectionResponseCreate,
) -> bool | None:
    if item.response_type == InspectionResponseType.boolean:
        if item.expected_bool is None:
            return None
        return response.value_bool == item.expected_bool
    if item.response_type == InspectionResponseType.text:
        if not item.expected_text_options or response.value_text is None:
            return None
        allowed = {_normalize_text(val) for val in item.expected_text_options}
        return _normalize_text(response.value_text) in allowed
    if item.response_type == InspectionResponseType.number:
        if response.value_number is None:
            return None
        if item.expected_number is not None:
            return response.value_number == item.expected_number
        if item.expected_number_min is None and item.expected_number_max is None:
            return None
        if (
            item.expected_number_min is not None
            and response.value_number < item.expected_number_min
        ):
            return False
        if (
            item.expected_number_max is not None
            and response.value_number > item.expected_number_max
        ):
            return False
        return True


def _as_utc(dt_value: datetime) -> datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=UTC)
    return dt_value.astimezone(UTC)


def _require_valid_calibration(session: Session, equipment: Equipment) -> None:
    equipment_type = session.get(EquipmentType, equipment.equipment_type_id)
    calibration_days = equipment_type.calibration_days if equipment_type else None
    latest = session.exec(
        select(EquipmentCalibration)
        .where(EquipmentCalibration.equipment_id == equipment.id)
        .order_by(desc(EquipmentCalibration.calibrated_at))  # type: ignore[arg-type]
    ).first()
    if not latest or not latest.calibrated_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El equipo no cuenta con calibración vigente.",
        )
    if calibration_days is None or calibration_days <= 0:
        return
    calibrated_at = _as_utc(latest.calibrated_at)
    expires_at = calibrated_at + timedelta(days=calibration_days)
    if datetime.now(UTC) > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El equipo no cuenta con calibración vigente.",
        )


@router.post(
    "/equipment/{equipment_id}",
    response_model=EquipmentInspectionRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_400_BAD_REQUEST: {"description": "Solicitud inválida"},
    },
)
def create_equipment_inspection(
    equipment_id: int,
    payload: EquipmentInspectionCreate,
    replace_existing: bool = Query(
        False,
        alias="replace_existing",
        description=(
            "Si es `true`, reemplaza la inspección abierta existente "
            "en lugar de crear una nueva."
        ),
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentInspectionRead:
    """
    Crea una inspección para un equipo.

    Permisos: `user`, `admin`, `superadmin`.
    Parámetros:
    - `replace_existing`: si es `true`, reemplaza la inspección abierta del día.
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

    if current_user.user_type != UserType.superadmin:
        allowed_terminal_ids = session.exec(
            select(UserTerminal.terminal_id).where(
                UserTerminal.user_id == current_user.id
            )
        ).all()
        if allowed_terminal_ids and equipment.terminal_id not in set(
            allowed_terminal_ids
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this terminal",
            )

    _require_valid_calibration(session, equipment)

    items = session.exec(
        select(EquipmentTypeInspectionItem).where(
            EquipmentTypeInspectionItem.equipment_type_id == equipment.equipment_type_id
        )
    ).all()
    items_by_id = {item.id: item for item in items if item.id is not None}
    required_ids = {item.id for item in items if item.is_required}

    response_item_ids = [r.inspection_item_id for r in payload.responses]
    if len(response_item_ids) != len(set(response_item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate inspection_item_id in responses",
        )
    if not required_ids.issubset(set(response_item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required inspection items",
        )

    evaluated_responses: list[
        tuple[EquipmentInspectionResponseCreate, bool | None]
    ] = []
    for response in payload.responses:
        if response.inspection_item_id not in items_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid inspection_item_id for this equipment type",
            )
        item = items_by_id[response.inspection_item_id]
        if response.response_type != item.response_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Response type does not match inspection item type",
            )
        _validate_response(
            response.response_type,
            response.value_bool,
            response.value_text,
            response.value_number,
        )
        evaluated_responses.append((response, _evaluate_response(item, response)))

    inspected_at = (
        _as_utc(payload.inspected_at) if payload.inspected_at else datetime.now(UTC)
    )
    now = datetime.now(UTC)
    if inspected_at.date() > now.date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inspección no puede ser posterior a hoy.",
        )
    day_start = datetime(
        inspected_at.year,
        inspected_at.month,
        inspected_at.day,
        tzinfo=UTC,
    )
    day_end = day_start + timedelta(days=1)
    existing_same_day = session.exec(
        select(EquipmentInspection).where(
            EquipmentInspection.equipment_id == equipment.id,
            EquipmentInspection.inspected_at >= day_start,
            EquipmentInspection.inspected_at < day_end,
        )
    ).first()
    if existing_same_day:
        if not replace_existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya se realizó una inspección hoy. ¿Deseas reemplazarla?",
            )
        if existing_same_day.id is not None:
            session.exec(
                delete(EquipmentInspectionResponse).where(
                    EquipmentInspectionResponse.inspection_id == existing_same_day.id  # type: ignore[arg-type]
                )
            )
            session.exec(
                delete(EquipmentInspection).where(
                    EquipmentInspection.id == existing_same_day.id  # type: ignore[arg-type]
                )
            )
            session.commit()
    inspection_ok = all(is_ok is True for _, is_ok in evaluated_responses)
    equipment_db_id = _require_id(equipment.id, "Equipment")
    inspection = EquipmentInspection(
        equipment_id=equipment_db_id,
        inspected_at=inspected_at,
        created_by_user_id=current_user.id,
        notes=payload.notes,
        is_ok=inspection_ok,
    )
    session.add(inspection)
    session.commit()
    session.refresh(inspection)
    inspection_db_id = _require_id(inspection.id, "Inspection")

    for response, is_ok in evaluated_responses:
        session.add(
            EquipmentInspectionResponse(
                inspection_id=inspection_db_id,
                inspection_item_id=response.inspection_item_id,
                response_type=response.response_type,
                value_bool=response.value_bool,
                value_text=response.value_text,
                value_number=response.value_number,
                is_ok=is_ok,
            )
        )
    session.commit()

    responses = session.exec(
        select(EquipmentInspectionResponse).where(
            EquipmentInspectionResponse.inspection_id == inspection_db_id
        )
    ).all()
    message: str | None = None
    if inspection_ok is False:
        equipment.status = EquipmentStatus.needs_review
        session.add(equipment)
        session.commit()
        message = "Inspection failed. Equipment status set to needs_review."
    if inspection_ok is True:
        equipment.status = EquipmentStatus.in_use
        session.add(equipment)
        session.commit()
    inspection_read = EquipmentInspectionRead.model_validate(
        inspection, from_attributes=True
    )
    inspection_read.responses = [
        EquipmentInspectionResponseRead.model_validate(r, from_attributes=True)
        for r in responses
    ]
    inspection_read.message = message
    return inspection_read


@router.get(
    "/equipment/{equipment_id}",
    response_model=EquipmentInspectionListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment_inspections(
    equipment_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> Any:
    """
    Lista inspecciones de un equipo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: equipo no encontrado.
    """
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    inspections = session.exec(
        select(EquipmentInspection).where(
            EquipmentInspection.equipment_id == equipment_id
        )
    ).all()
    if not inspections:
        return EquipmentInspectionListResponse(message="No records found")

    items: list[EquipmentInspectionRead] = []
    for inspection in inspections:
        responses = session.exec(
            select(EquipmentInspectionResponse).where(
                EquipmentInspectionResponse.inspection_id == inspection.id
            )
        ).all()
        items.append(
            EquipmentInspectionRead(
                **inspection.model_dump(),
                responses=[
                    EquipmentInspectionResponseRead.model_validate(
                        r, from_attributes=True
                    )
                    for r in responses
                ],
            )
        )
    return EquipmentInspectionListResponse(items=items)


@router.get(
    "/{inspection_id}",
    response_model=EquipmentInspectionRead,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def get_equipment_inspection(
    inspection_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> EquipmentInspectionRead:
    """
    Obtiene una inspección por ID.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    """
    inspection = session.get(EquipmentInspection, inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )
    responses = session.exec(
        select(EquipmentInspectionResponse).where(
            EquipmentInspectionResponse.inspection_id == inspection.id
        )
    ).all()
    return EquipmentInspectionRead(
        **inspection.model_dump(),
        responses=[
            EquipmentInspectionResponseRead.model_validate(r, from_attributes=True)
            for r in responses
        ],
    )


@router.patch(
    "/{inspection_id}",
    response_model=EquipmentInspectionRead,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_equipment_inspection(
    inspection_id: int,
    payload: EquipmentInspectionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentInspectionRead:
    """
    Actualiza una inspección existente por ID.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    inspection = session.get(EquipmentInspection, inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    equipment = session.get(Equipment, inspection.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    if current_user.user_type != UserType.superadmin:
        allowed_terminal_ids = session.exec(
            select(UserTerminal.terminal_id).where(
                UserTerminal.user_id == current_user.id
            )
        ).all()
        if allowed_terminal_ids and equipment.terminal_id not in set(
            allowed_terminal_ids
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this terminal",
            )

    items = session.exec(
        select(EquipmentTypeInspectionItem).where(
            EquipmentTypeInspectionItem.equipment_type_id == equipment.equipment_type_id
        )
    ).all()
    items_by_id = {item.id: item for item in items if item.id is not None}
    required_ids = {item.id for item in items if item.is_required}

    response_item_ids = [r.inspection_item_id for r in payload.responses]
    if len(response_item_ids) != len(set(response_item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate inspection_item_id in responses",
        )
    if not required_ids.issubset(set(response_item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required inspection items",
        )

    evaluated_responses: list[
        tuple[EquipmentInspectionResponseCreate, bool | None]
    ] = []
    for response in payload.responses:
        if response.inspection_item_id not in items_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid inspection_item_id for this equipment type",
            )
        item = items_by_id[response.inspection_item_id]
        if response.response_type != item.response_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Response type does not match inspection item type",
            )
        _validate_response(
            response.response_type,
            response.value_bool,
            response.value_text,
            response.value_number,
        )
        evaluated_responses.append((response, _evaluate_response(item, response)))

    inspected_at = (
        _as_utc(payload.inspected_at)
        if payload.inspected_at
        else _as_utc(inspection.inspected_at)
    )
    now = datetime.now(UTC)
    if inspected_at.date() > now.date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inspección no puede ser posterior a hoy.",
        )
    day_start = datetime(
        inspected_at.year,
        inspected_at.month,
        inspected_at.day,
        tzinfo=UTC,
    )
    day_end = day_start + timedelta(days=1)
    existing_same_day = session.exec(
        select(EquipmentInspection).where(
            EquipmentInspection.equipment_id == equipment.id,
            EquipmentInspection.inspected_at >= day_start,
            EquipmentInspection.inspected_at < day_end,
            EquipmentInspection.id != inspection.id,
        )
    ).first()
    if existing_same_day:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una inspección para esta fecha.",
        )

    inspection_ok = all(is_ok is True for _, is_ok in evaluated_responses)
    inspection.inspected_at = inspected_at
    inspection.notes = payload.notes
    inspection.is_ok = inspection_ok
    session.add(inspection)
    inspection_db_id = _require_id(inspection.id, "Inspection")
    session.exec(
        delete(EquipmentInspectionResponse).where(
            EquipmentInspectionResponse.inspection_id == inspection_db_id  # type: ignore[arg-type]
        )
    )
    for response, is_ok in evaluated_responses:
        session.add(
            EquipmentInspectionResponse(
                inspection_id=inspection_db_id,
                inspection_item_id=response.inspection_item_id,
                response_type=response.response_type,
                value_bool=response.value_bool,
                value_text=response.value_text,
                value_number=response.value_number,
                is_ok=is_ok,
            )
        )
    session.commit()
    session.refresh(inspection)

    responses = session.exec(
        select(EquipmentInspectionResponse).where(
            EquipmentInspectionResponse.inspection_id == inspection_db_id
        )
    ).all()
    message: str | None = None
    if inspection_ok is False:
        equipment.status = EquipmentStatus.needs_review
        session.add(equipment)
        session.commit()
        message = "Inspection failed. Equipment status set to needs_review."
    if inspection_ok is True:
        equipment.status = EquipmentStatus.in_use
        session.add(equipment)
        session.commit()
    inspection_read = EquipmentInspectionRead.model_validate(
        inspection, from_attributes=True
    )
    inspection_read.responses = [
        EquipmentInspectionResponseRead.model_validate(r, from_attributes=True)
        for r in responses
    ]
    inspection_read.message = message
    return inspection_read
