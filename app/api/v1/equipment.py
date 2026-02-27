from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, delete, select

from app.api.v1.equipment_verifications import _parse_monthly_readings_from_notes
from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.company import Company
from app.models.company_terminal import CompanyTerminal
from app.models.enums import EquipmentMeasureType, UserType
from app.models.equipment import (
    Equipment,
    EquipmentComponentSerial,
    EquipmentComponentSerialCreate,
    EquipmentComponentSerialRead,
    EquipmentCreate,
    EquipmentDeleteResponse,
    EquipmentListResponse,
    EquipmentReadWithIncludes,
    EquipmentUpdate,
)
from app.models.equipment_calibration import (
    EquipmentCalibration,
    EquipmentCalibrationRead,
    EquipmentCalibrationResult,
    EquipmentCalibrationResultRead,
)
from app.models.equipment_history import (
    EquipmentHistoryEntry,
    EquipmentHistoryListResponse,
)
from app.models.equipment_inspection import (
    EquipmentInspection,
    EquipmentInspectionRead,
    EquipmentInspectionResponse,
    EquipmentInspectionResponseRead,
)
from app.models.equipment_measure_spec import (
    EquipmentMeasureSpec,
    EquipmentMeasureSpecCreate,
    EquipmentMeasureSpecRead,
)
from app.models.equipment_reading import EquipmentReading
from app.models.equipment_terminal_history import (
    EquipmentTerminalHistory,
    EquipmentTerminalHistoryListResponse,
    EquipmentTerminalHistoryRead,
)
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_history import (
    EquipmentTypeHistory,
    EquipmentTypeHistoryListResponse,
    EquipmentTypeHistoryRead,
)
from app.models.equipment_verification import (
    EquipmentVerification,
    EquipmentVerificationRead,
    EquipmentVerificationResponse,
    EquipmentVerificationResponseRead,
)
from app.models.refs import CompanyRef, CompanyTerminalRef, EquipmentTypeRef, UserRef
from app.models.user import User
from app.models.user_terminal import UserTerminal
from app.utils.emp_weights import get_emp
from app.utils.measurements.length import Length
from app.utils.measurements.temperature import Temperature
from app.utils.measurements.weight import Weight

router = APIRouter(
    prefix="/equipment",
    tags=["Equipment"],
)


def _get_allowed_terminal_ids(session: Session, user: User) -> set[int]:
    if user.user_type == UserType.superadmin:
        return set()
    links = session.exec(
        select(UserTerminal).where(UserTerminal.user_id == user.id)
    ).all()
    return {link.terminal_id for link in links}


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


def _normalize_weight(value: float, unit: str) -> float:
    unit_key = unit.strip().lower()
    try:
        if unit_key in {"g", "gram", "grams"}:
            return Weight.from_grams(value).as_grams
        if unit_key in {"kg", "kilogram", "kilograms"}:
            return Weight.from_kilograms(value).as_grams
        if unit_key in {"lb", "lbs", "pound", "pounds"}:
            return Weight.from_pounds(value).as_grams
        if unit_key in {"oz", "ounce", "ounces"}:
            return Weight.from_ounces(value).as_grams
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported weight unit",
    )


def _normalize_length(value: float, unit: str) -> float:
    unit_key = unit.strip().lower()
    try:
        if unit_key in {"mm", "millimeter", "millimeters"}:
            return Length.from_millimeters(value).as_millimeters
        if unit_key in {"cm", "centimeter", "centimeters"}:
            return Length.from_centimeters(value).as_millimeters
        if unit_key in {"m", "meter", "meters"}:
            return Length.from_meters(value).as_millimeters
        if unit_key in {"in", "inch", "inches"}:
            return Length.from_inches(value).as_millimeters
        if unit_key in {"ft", "foot", "feet"}:
            return Length.from_feet(value).as_millimeters
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported length unit",
    )


def _normalize_api(value: float, unit: str) -> float:
    unit_key = unit.strip().lower()
    if unit_key in {"api"}:
        return value
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported API unit",
    )


def _normalize_percent_pv(value: float, unit: str) -> float:
    unit_key = unit.strip().lower().replace(" ", "")
    if unit_key in {"%p/v", "%pv", "p/v", "%w/v"}:
        return value
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported percent p/v unit",
    )


def _normalize_relative_humidity(value: float, unit: str) -> float:
    unit_key = unit.strip().lower().replace(" ", "")
    if unit_key in {"%", "%rh", "rh", "percent", "relativehumidity"}:
        return value
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported relative humidity unit",
    )


def _to_equipment_type_ref(model: EquipmentType) -> EquipmentTypeRef:
    return EquipmentTypeRef(
        **model.model_dump(
            include={
                "id",
                "name",
                "role",
                "inspection_days",
                "calibration_days",
                "is_lab",
            }
        )
    )


def _to_company_ref(model: Company) -> CompanyRef:
    return CompanyRef(
        **model.model_dump(include={"id", "name", "company_type", "is_active"})
    )


def _to_terminal_ref(model: CompanyTerminal) -> CompanyTerminalRef:
    return CompanyTerminalRef(**model.model_dump(include={"id", "name", "is_active"}))


def _to_user_ref(model: User) -> UserRef:
    return UserRef(
        **model.model_dump(include={"id", "name", "last_name", "email", "user_type"})
    )


def _format_nominal_mass(value: float) -> str:
    numeric = float(value)
    if numeric.is_integer():
        return str(int(numeric))
    return str(numeric).rstrip("0").rstrip(".")


def _validate_weight_serial(serial: str, nominal_mass_value: float, unit: str) -> None:
    if not serial:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serial is required",
        )
    unit_key = str(unit or "").strip().lower()
    if unit_key != "g":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Serial validation only supports unit g",
        )
    expected = f"{_format_nominal_mass(nominal_mass_value)}G"
    serial_norm = serial.strip().upper().replace(" ", "")
    if not serial_norm.endswith(expected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Serial must end with {expected}",
        )


def _replace_component_serials(
    session: Session,
    equipment_id: int,
    component_serials: list[EquipmentComponentSerialCreate],
) -> None:
    session.exec(
        delete(EquipmentComponentSerial).where(
            EquipmentComponentSerial.equipment_id == equipment_id  # type: ignore[arg-type]
        )
    )
    for component in component_serials:
        session.add(
            EquipmentComponentSerial(
                equipment_id=equipment_id,
                component_name=component.component_name.strip(),
                serial=component.serial.strip(),
            )
        )


def _get_component_serials(
    session: Session,
    equipment_id: int,
) -> list[EquipmentComponentSerialRead]:
    rows = session.exec(
        select(EquipmentComponentSerial).where(
            EquipmentComponentSerial.equipment_id == equipment_id
        )
    ).all()
    return [EquipmentComponentSerialRead(**row.model_dump()) for row in rows]


@router.post(
    "/",
    response_model=EquipmentReadWithIncludes,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def create_equipment(
    equipment_in: EquipmentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentReadWithIncludes:
    """
    Crea un equipo con especificaciones de medida y componentes.

    Permisos: `admin`, `superadmin`.
    Respuestas:
    - 400: solicitud inválida.
    - 403: permisos insuficientes.
    - 404: tipo de equipo, empresa o terminal no encontrada.

    Nota: valida el EMP y el serial para pesas. Registra el historial
    inicial de tipo y terminal del equipo.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    equipment_type = session.get(EquipmentType, equipment_in.equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    owner_company = session.get(Company, equipment_in.owner_company_id)
    if not owner_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner company not found",
        )
    terminal = session.get(CompanyTerminal, equipment_in.terminal_id)
    if not terminal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal not found",
        )

    emp_value = None
    weight_class = equipment_in.weight_class
    nominal_mass_value = equipment_in.nominal_mass_value
    nominal_mass_unit = equipment_in.nominal_mass_unit
    if (
        weight_class is not None
        or nominal_mass_value is not None
        or nominal_mass_unit is not None
    ):
        if not weight_class or nominal_mass_value is None or not nominal_mass_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="weight_class, nominal_mass_value and nominal_mass_unit are required together",
            )
        try:
            emp_value = get_emp(weight_class, nominal_mass_value, nominal_mass_unit)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        _validate_weight_serial(
            equipment_in.serial, nominal_mass_value, nominal_mass_unit
        )

    equipment = Equipment(
        serial=equipment_in.serial,
        model=equipment_in.model,
        brand=equipment_in.brand,
        status=equipment_in.status,
        is_active=equipment_in.is_active,
        inspection_days_override=equipment_in.inspection_days_override,
        equipment_type_id=equipment_in.equipment_type_id,
        owner_company_id=equipment_in.owner_company_id,
        terminal_id=equipment_in.terminal_id,
        created_by_user_id=current_user.id,
        weight_class=weight_class,
        nominal_mass_value=nominal_mass_value,
        nominal_mass_unit=nominal_mass_unit,
        emp_value=emp_value,
    )

    session.add(equipment)
    session.commit()
    session.refresh(equipment)
    if equipment.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Equipment has no ID after creation",
        )
    equipment_id = equipment.id

    session.add(
        EquipmentTypeHistory(
            equipment_id=equipment_id,
            equipment_type_id=equipment.equipment_type_id,
            changed_by_user_id=current_user.id,
        )
    )
    session.add(
        EquipmentTerminalHistory(
            equipment_id=equipment_id,
            terminal_id=equipment.terminal_id,
            changed_by_user_id=current_user.id,
        )
    )
    session.commit()

    _replace_component_serials(
        session,
        equipment_id,
        equipment_in.component_serials,
    )

    for spec in equipment_in.measure_specs:
        if spec.measure not in {
            EquipmentMeasureType.temperature,
            EquipmentMeasureType.weight,
            EquipmentMeasureType.length,
            EquipmentMeasureType.api,
            EquipmentMeasureType.percent_pv,
            EquipmentMeasureType.relative_humidity,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit conversion not implemented for this measure",
            )
        if not spec.min_unit or not spec.max_unit or not spec.resolution_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_unit, max_unit and resolution_unit are required for each measure",
            )
        if spec.min_value is None or spec.max_value is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_value and max_value are required for each measure",
            )
        if spec.measure == EquipmentMeasureType.temperature:
            min_value = _normalize_temperature(spec.min_value, spec.min_unit)
            max_value = _normalize_temperature(spec.max_value, spec.max_unit)
            resolution = (
                _normalize_temperature(spec.resolution, spec.resolution_unit)
                if spec.resolution is not None
                else None
            )
        elif spec.measure == EquipmentMeasureType.weight:
            min_value = _normalize_weight(spec.min_value, spec.min_unit)
            max_value = _normalize_weight(spec.max_value, spec.max_unit)
            resolution = (
                _normalize_weight(spec.resolution, spec.resolution_unit)
                if spec.resolution is not None
                else None
            )
        elif spec.measure == EquipmentMeasureType.api:
            min_value = _normalize_api(spec.min_value, spec.min_unit)
            max_value = _normalize_api(spec.max_value, spec.max_unit)
            resolution = (
                _normalize_api(spec.resolution, spec.resolution_unit)
                if spec.resolution is not None
                else None
            )
        elif spec.measure == EquipmentMeasureType.percent_pv:
            min_value = _normalize_percent_pv(spec.min_value, spec.min_unit)
            max_value = _normalize_percent_pv(spec.max_value, spec.max_unit)
            resolution = (
                _normalize_percent_pv(spec.resolution, spec.resolution_unit)
                if spec.resolution is not None
                else None
            )
        elif spec.measure == EquipmentMeasureType.relative_humidity:
            min_value = _normalize_relative_humidity(spec.min_value, spec.min_unit)
            max_value = _normalize_relative_humidity(spec.max_value, spec.max_unit)
            resolution = (
                _normalize_relative_humidity(spec.resolution, spec.resolution_unit)
                if spec.resolution is not None
                else None
            )
        else:
            min_value = _normalize_length(spec.min_value, spec.min_unit)
            max_value = _normalize_length(spec.max_value, spec.max_unit)
            resolution = (
                _normalize_length(spec.resolution, spec.resolution_unit)
                if spec.resolution is not None
                else None
            )
        if min_value > max_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_value cannot be greater than max_value",
            )
        if resolution is not None and resolution <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="resolution must be greater than zero",
            )
        session.add(
            EquipmentMeasureSpec(
                equipment_id=equipment_id,
                measure=spec.measure,
                min_value=min_value,
                max_value=max_value,
                resolution=resolution,
            )
        )
    session.commit()

    response = EquipmentReadWithIncludes.model_validate(
        equipment,
        from_attributes=True,
    )
    measure_specs = session.exec(
        select(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equipment_id
        )
    ).all()
    response.measure_specs = [
        EquipmentMeasureSpecRead(**s.model_dump()) for s in measure_specs
    ]
    response.component_serials = _get_component_serials(session, equipment_id)
    return response


@router.get(
    "/",
    response_model=EquipmentListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment(
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
    include: str | None = Query(
        default=None,
        description=(
            "Relaciones a incluir, separadas por coma: `equipment_type`, "
            "`owner_company`, `terminal`."
        ),
    ),
) -> Any:
    """
    Lista equipos visibles para el usuario actual.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Parámetros:
    - `include`: relaciones opcionales (`equipment_type`, `owner_company`,
      `terminal`, `creator`, `inspections`, `verifications`, `calibrations`).

    Nota: usuarios que no son `superadmin` solo ven equipos de las
    terminales que tienen asignadas.
    """
    statement = select(Equipment)
    allowed_terminal_ids = _get_allowed_terminal_ids(session, current_user)
    if allowed_terminal_ids:
        statement = statement.where(
            Equipment.terminal_id.in_(allowed_terminal_ids)  # type: ignore[attr-defined]
        )
    equipment_items = session.exec(statement).all()
    if not equipment_items:
        return EquipmentListResponse(message="No records found")
    include_set = {item.strip() for item in (include or "").split(",") if item.strip()}
    items: list[EquipmentReadWithIncludes] = []
    for equipment in equipment_items:
        if equipment.id is None:
            continue
        equipment_id = equipment.id
        measure_specs = session.exec(
            select(EquipmentMeasureSpec).where(
                EquipmentMeasureSpec.equipment_id == equipment_id
            )
        ).all()
        item = EquipmentReadWithIncludes.model_validate(
            equipment,
            from_attributes=True,
        )
        item.measure_specs = [
            EquipmentMeasureSpecRead(**s.model_dump()) for s in measure_specs
        ]
        item.component_serials = _get_component_serials(session, equipment_id)
        if include_set:
            if "equipment_type" in include_set:
                equipment_type = session.get(
                    EquipmentType, equipment.equipment_type_id
                )
                if equipment_type:
                    item.equipment_type = _to_equipment_type_ref(equipment_type)
            if "owner_company" in include_set:
                owner_company = session.get(Company, equipment.owner_company_id)
                if owner_company:
                    item.owner_company = _to_company_ref(owner_company)
            if "terminal" in include_set:
                terminal = session.get(CompanyTerminal, equipment.terminal_id)
                if terminal:
                    item.terminal = _to_terminal_ref(terminal)
            if "creator" in include_set:
                creator = session.get(User, equipment.created_by_user_id)
                if creator:
                    item.creator = _to_user_ref(creator)
            if "inspections" in include_set:
                inspections = session.exec(
                    select(EquipmentInspection).where(
                        EquipmentInspection.equipment_id == equipment_id
                    )
                ).all()
                inspection_items: list[EquipmentInspectionRead] = []
                for inspection in inspections:
                    inspection_responses = session.exec(
                        select(EquipmentInspectionResponse).where(
                            EquipmentInspectionResponse.inspection_id == inspection.id
                        )
                    ).all()
                    inspection_items.append(
                        EquipmentInspectionRead(
                            **inspection.model_dump(),
                            responses=[
                                EquipmentInspectionResponseRead(**r.model_dump())
                                for r in inspection_responses
                            ],
                        )
                    )
                item.inspections = inspection_items
            if "verifications" in include_set:
                verifications = session.exec(
                    select(EquipmentVerification).where(
                        EquipmentVerification.equipment_id == equipment_id
                    )
                ).all()
                verification_items: list[EquipmentVerificationRead] = []
                for verification in verifications:
                    verification_responses = session.exec(
                        select(EquipmentVerificationResponse).where(
                            EquipmentVerificationResponse.verification_id
                            == verification.id
                        )
                    ).all()
                    verification_items.append(
                        EquipmentVerificationRead(
                            **verification.model_dump(),
                            responses=[
                                EquipmentVerificationResponseRead(**r.model_dump())
                                for r in verification_responses
                            ],
                        )
                    )
                    monthly = _parse_monthly_readings_from_notes(verification.notes)
                    if monthly:
                        for key, value in monthly.items():
                            setattr(verification_items[-1], key, value)
                item.verifications = verification_items
            if "calibrations" in include_set:
                calibrations = session.exec(
                    select(EquipmentCalibration).where(
                        EquipmentCalibration.equipment_id == equipment_id
                    )
                ).all()
                calibration_items: list[EquipmentCalibrationRead] = []
                for calibration in calibrations:
                    results = session.exec(
                        select(EquipmentCalibrationResult).where(
                            EquipmentCalibrationResult.calibration_id == calibration.id
                        )
                    ).all()
                    calibration_items.append(
                        EquipmentCalibrationRead(
                            **calibration.model_dump(),
                            results=[
                                EquipmentCalibrationResultRead(**r.model_dump())
                                for r in results
                            ],
                        )
                    )
                item.calibrations = calibration_items
        items.append(item)
    return EquipmentListResponse(items=items)


@router.get(
    "/{equipment_id}",
    response_model=EquipmentReadWithIncludes,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def get_equipment(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
    include: str | None = Query(
        default=None,
        description=(
            "Relaciones a incluir, separadas por coma: `equipment_type`, "
            "`owner_company`, `terminal`."
        ),
    ),
) -> EquipmentReadWithIncludes:
    """
    Obtiene un equipo por ID con relaciones opcionales.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Parámetros:
    - `include`: relaciones opcionales (`equipment_type`, `owner_company`,
      `terminal`, `creator`, `inspections`, `verifications`, `calibrations`).
    Respuestas:
    - 403: sin acceso a la terminal del equipo.
    - 404: equipo no encontrado.
    """
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    allowed_terminal_ids = _get_allowed_terminal_ids(session, current_user)
    if allowed_terminal_ids and equipment.terminal_id not in allowed_terminal_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this terminal",
        )
    if equipment.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Equipment has no ID",
        )
    equip_id = equipment.id
    if equipment.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Equipment has no ID",
        )
    equip_id = equipment.id
    if equipment.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Equipment has no ID",
        )
    equip_id = equipment.id
    response = EquipmentReadWithIncludes.model_validate(
        equipment,
        from_attributes=True,
    )
    if equipment.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Equipment has no ID",
        )
    equip_id = equipment.id
    measure_specs = session.exec(
        select(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equip_id
        )
    ).all()
    response.measure_specs = [
        EquipmentMeasureSpecRead(**s.model_dump()) for s in measure_specs
    ]
    response.component_serials = _get_component_serials(session, equip_id)
    include_set = {item.strip() for item in (include or "").split(",") if item.strip()}
    if include_set:
        if "equipment_type" in include_set:
            equipment_type = session.get(EquipmentType, equipment.equipment_type_id)
            if equipment_type:
                response.equipment_type = _to_equipment_type_ref(equipment_type)
        if "owner_company" in include_set:
            owner_company = session.get(Company, equipment.owner_company_id)
            if owner_company:
                response.owner_company = _to_company_ref(owner_company)
        if "terminal" in include_set:
            terminal = session.get(CompanyTerminal, equipment.terminal_id)
            if terminal:
                response.terminal = _to_terminal_ref(terminal)
        if "creator" in include_set:
            creator = session.get(User, equipment.created_by_user_id)
            if creator:
                response.creator = _to_user_ref(creator)
        if "inspections" in include_set:
            inspections = session.exec(
                select(EquipmentInspection).where(
                    EquipmentInspection.equipment_id == equip_id
                )
            ).all()
            inspection_items: list[EquipmentInspectionRead] = []
            for inspection in inspections:
                inspection_responses = session.exec(
                    select(EquipmentInspectionResponse).where(
                        EquipmentInspectionResponse.inspection_id == inspection.id
                    )
                ).all()
                inspection_items.append(
                    EquipmentInspectionRead(
                        **inspection.model_dump(),
                        responses=[
                            EquipmentInspectionResponseRead(**r.model_dump())
                            for r in inspection_responses
                        ],
                    )
                )
            response.inspections = inspection_items
        if "verifications" in include_set:
            verifications = session.exec(
                select(EquipmentVerification).where(
                    EquipmentVerification.equipment_id == equip_id
                )
            ).all()
            verification_items: list[EquipmentVerificationRead] = []
            for verification in verifications:
                verification_responses = session.exec(
                    select(EquipmentVerificationResponse).where(
                        EquipmentVerificationResponse.verification_id == verification.id
                    )
                ).all()
                verification_items.append(
                    EquipmentVerificationRead(
                        **verification.model_dump(),
                        responses=[
                            EquipmentVerificationResponseRead(**r.model_dump())
                            for r in verification_responses
                        ],
                    )
                )
                monthly = _parse_monthly_readings_from_notes(verification.notes)
                if monthly:
                    for key, value in monthly.items():
                        setattr(verification_items[-1], key, value)
            response.verifications = verification_items
        if "calibrations" in include_set:
            calibrations = session.exec(
                select(EquipmentCalibration).where(
                    EquipmentCalibration.equipment_id == equip_id
                )
            ).all()
            calibration_items: list[EquipmentCalibrationRead] = []
            for calibration in calibrations:
                results = session.exec(
                    select(EquipmentCalibrationResult).where(
                        EquipmentCalibrationResult.calibration_id == calibration.id
                    )
                ).all()
                calibration_items.append(
                    EquipmentCalibrationRead(
                        **calibration.model_dump(),
                        results=[
                            EquipmentCalibrationResultRead(**r.model_dump())
                            for r in results
                        ],
                    )
                )
            response.calibrations = calibration_items
    return response


@router.patch(
    "/{equipment_id}",
    response_model=EquipmentReadWithIncludes,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentReadWithIncludes:
    """
    Actualiza un equipo y sus relaciones dependientes.

    Permisos: `user`, `admin`, `superadmin`.
    Respuestas:
    - 400: solicitud inválida.
    - 403: permisos insuficientes o sin acceso a la terminal.
    - 404: equipo, tipo de equipo o terminal no encontrada.

    Nota: puede actualizar especificaciones de medida y seriales de
    componentes. Registra cambios de tipo o terminal en el historial.
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
    allowed_terminal_ids = _get_allowed_terminal_ids(session, current_user)
    if allowed_terminal_ids and equipment.terminal_id not in allowed_terminal_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this terminal",
        )
    if equipment.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Equipment has no ID",
        )
    equip_id = equipment.id

    update_data = payload.model_dump(exclude_unset=True)
    specs = update_data.pop("measure_specs", None)
    component_serials = update_data.pop("component_serials", None)

    if {
        "weight_class",
        "nominal_mass_value",
        "nominal_mass_unit",
    } & set(update_data.keys()):
        weight_class = update_data.get("weight_class")
        nominal_mass_value = update_data.get("nominal_mass_value")
        nominal_mass_unit = update_data.get("nominal_mass_unit")
        if not weight_class and nominal_mass_value is None and not nominal_mass_unit:
            update_data["weight_class"] = None
            update_data["nominal_mass_value"] = None
            update_data["nominal_mass_unit"] = None
            update_data["emp_value"] = None
        else:
            if not weight_class or nominal_mass_value is None or not nominal_mass_unit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="weight_class, nominal_mass_value and nominal_mass_unit are required together",
                )
            try:
                update_data["emp_value"] = get_emp(
                    weight_class, nominal_mass_value, nominal_mass_unit
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            serial_to_check = update_data.get("serial", equipment.serial)
            _validate_weight_serial(
                serial_to_check, nominal_mass_value, nominal_mass_unit
            )

    if "equipment_type_id" in update_data:
        equipment_type_id = update_data["equipment_type_id"]
        if equipment_type_id is not None:
            equipment_type = session.get(EquipmentType, equipment_type_id)
            if not equipment_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Equipment type not found",
                )
            if equipment_type_id != equipment.equipment_type_id:
                current_type_history = session.exec(
                    select(EquipmentTypeHistory).where(
                        EquipmentTypeHistory.equipment_id == equip_id,
                        EquipmentTypeHistory.ended_at.is_(None),  # type: ignore[union-attr]
                    )
                ).first()
                if current_type_history:
                    current_type_history.ended_at = datetime.now(UTC)
                    session.add(current_type_history)

                session.add(
                    EquipmentTypeHistory(
                        equipment_id=equip_id,
                        equipment_type_id=equipment_type_id,
                        changed_by_user_id=current_user.id,
                    )
                )

    if "owner_company_id" in update_data:
        owner_company_id = update_data["owner_company_id"]
        if owner_company_id is not None and not session.get(Company, owner_company_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Owner company not found",
            )

    if "terminal_id" in update_data:
        terminal_id = update_data["terminal_id"]
        if terminal_id is not None and not session.get(CompanyTerminal, terminal_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Terminal not found",
            )
        if allowed_terminal_ids and terminal_id not in allowed_terminal_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this terminal",
            )
        if terminal_id is not None and terminal_id != equipment.terminal_id:
            current_terminal_history = session.exec(
                select(EquipmentTerminalHistory).where(
                    EquipmentTerminalHistory.equipment_id == equip_id,
                    EquipmentTerminalHistory.ended_at.is_(None),  # type: ignore[union-attr]
                )
            ).first()
            if current_terminal_history:
                current_terminal_history.ended_at = datetime.now(UTC)
                session.add(current_terminal_history)
            session.add(
                EquipmentTerminalHistory(
                    equipment_id=equip_id,
                    terminal_id=terminal_id,
                    changed_by_user_id=current_user.id,
                )
            )

    for field, value in update_data.items():
        setattr(equipment, field, value)

    session.add(equipment)
    session.commit()
    session.refresh(equipment)

    if component_serials is not None:
        _replace_component_serials(
            session,
            equip_id,
            [
                (
                    EquipmentComponentSerialCreate.model_validate(item)
                    if isinstance(item, dict)
                    else item
                )
                for item in component_serials
            ],
        )

    if specs is not None:
        session.exec(
            delete(EquipmentMeasureSpec).where(
                EquipmentMeasureSpec.equipment_id == equip_id  # type: ignore[arg-type]
            )
        )
        for spec_data in specs:
            spec = (
                EquipmentMeasureSpecCreate.model_validate(spec_data)
                if isinstance(spec_data, dict)
                else spec_data
            )
            if spec.measure not in {
                EquipmentMeasureType.temperature,
                EquipmentMeasureType.weight,
                EquipmentMeasureType.length,
                EquipmentMeasureType.api,
                EquipmentMeasureType.percent_pv,
                EquipmentMeasureType.relative_humidity,
            }:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unit conversion not implemented for this measure",
                )
            if not spec.min_unit or not spec.max_unit or not spec.resolution_unit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="min_unit, max_unit and resolution_unit are required for each measure",
                )
            if spec.min_value is None or spec.max_value is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="min_value and max_value are required for each measure",
                )
            if spec.measure == EquipmentMeasureType.temperature:
                min_value = _normalize_temperature(spec.min_value, spec.min_unit)
                max_value = _normalize_temperature(spec.max_value, spec.max_unit)
                resolution = (
                    _normalize_temperature(spec.resolution, spec.resolution_unit)
                    if spec.resolution is not None
                    else None
                )
            elif spec.measure == EquipmentMeasureType.weight:
                min_value = _normalize_weight(spec.min_value, spec.min_unit)
                max_value = _normalize_weight(spec.max_value, spec.max_unit)
                resolution = (
                    _normalize_weight(spec.resolution, spec.resolution_unit)
                    if spec.resolution is not None
                    else None
                )
            elif spec.measure == EquipmentMeasureType.api:
                min_value = _normalize_api(spec.min_value, spec.min_unit)
                max_value = _normalize_api(spec.max_value, spec.max_unit)
                resolution = (
                    _normalize_api(spec.resolution, spec.resolution_unit)
                    if spec.resolution is not None
                    else None
                )
            elif spec.measure == EquipmentMeasureType.percent_pv:
                min_value = _normalize_percent_pv(spec.min_value, spec.min_unit)
                max_value = _normalize_percent_pv(spec.max_value, spec.max_unit)
                resolution = (
                    _normalize_percent_pv(spec.resolution, spec.resolution_unit)
                    if spec.resolution is not None
                    else None
                )
            elif spec.measure == EquipmentMeasureType.relative_humidity:
                min_value = _normalize_relative_humidity(spec.min_value, spec.min_unit)
                max_value = _normalize_relative_humidity(spec.max_value, spec.max_unit)
                resolution = (
                    _normalize_relative_humidity(spec.resolution, spec.resolution_unit)
                    if spec.resolution is not None
                    else None
                )
            else:
                min_value = _normalize_length(spec.min_value, spec.min_unit)
                max_value = _normalize_length(spec.max_value, spec.max_unit)
                resolution = (
                    _normalize_length(spec.resolution, spec.resolution_unit)
                    if spec.resolution is not None
                    else None
                )
            if min_value > max_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="min_value cannot be greater than max_value",
                )
            if resolution is not None and resolution <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="resolution must be greater than zero",
                )
            session.add(
                EquipmentMeasureSpec(
                    equipment_id=equip_id,
                    measure=spec.measure,
                    min_value=min_value,
                    max_value=max_value,
                    resolution=resolution,
                )
            )
        session.commit()
    elif component_serials is not None:
        session.commit()

    response = EquipmentReadWithIncludes.model_validate(
        equipment,
        from_attributes=True,
    )
    measure_specs = session.exec(
        select(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equip_id
        )
    ).all()
    response.measure_specs = [
        EquipmentMeasureSpecRead(**s.model_dump()) for s in measure_specs
    ]
    response.component_serials = _get_component_serials(session, equip_id)
    return response


@router.delete(
    "/{equipment_id}",
    response_model=EquipmentDeleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def delete_equipment(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentDeleteResponse:
    """
    Elimina un equipo o lo desactiva si tiene operaciones asociadas.

    Permisos: `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes o sin acceso a la terminal.
    - 404: equipo no encontrado.

    Nota: si el equipo tiene inspecciones, verificaciones, calibraciones
    o lecturas registradas, se desactiva en lugar de eliminarse.
    """
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    allowed_terminal_ids = _get_allowed_terminal_ids(session, current_user)
    if allowed_terminal_ids and equipment.terminal_id not in allowed_terminal_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this terminal",
        )
    if equipment.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Equipment has no ID",
        )
    equip_id = equipment.id

    has_inspection = session.exec(
        select(EquipmentInspection.id).where(
            EquipmentInspection.equipment_id == equip_id
        )
    ).first()
    has_reading = session.exec(
        select(EquipmentReading.id).where(EquipmentReading.equipment_id == equip_id)
    ).first()
    has_calibration = session.exec(
        select(EquipmentCalibration.id).where(
            EquipmentCalibration.equipment_id == equip_id
        )
    ).first()

    if has_inspection or has_reading or has_calibration:
        equipment.is_active = False
        session.add(equipment)
        session.commit()
        session.refresh(equipment)
        response = EquipmentReadWithIncludes.model_validate(
            equipment, from_attributes=True
        )
        equipment_type = session.get(EquipmentType, equipment.equipment_type_id)
        if equipment_type:
            response.equipment_type = _to_equipment_type_ref(equipment_type)
        owner_company = session.get(Company, equipment.owner_company_id)
        if owner_company:
            response.owner_company = _to_company_ref(owner_company)
        terminal = session.get(CompanyTerminal, equipment.terminal_id)
        if terminal:
            response.terminal = _to_terminal_ref(terminal)
        response.component_serials = _get_component_serials(session, equip_id)
        return EquipmentDeleteResponse(
            action="deactivated",
            message="Equipment has operations. It was marked inactive instead of deleted.",
            equipment=response,
        )

    equipment_data = EquipmentReadWithIncludes.model_validate(
        equipment, from_attributes=True
    )
    equipment_type = session.get(EquipmentType, equipment.equipment_type_id)
    if equipment_type:
        equipment_data.equipment_type = _to_equipment_type_ref(equipment_type)
    owner_company = session.get(Company, equipment.owner_company_id)
    if owner_company:
        equipment_data.owner_company = _to_company_ref(owner_company)
    terminal = session.get(CompanyTerminal, equipment.terminal_id)
    if terminal:
        equipment_data.terminal = _to_terminal_ref(terminal)
    equipment_data.component_serials = _get_component_serials(session, equip_id)

    session.exec(
        delete(EquipmentComponentSerial).where(
            EquipmentComponentSerial.equipment_id == equip_id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equip_id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentTypeHistory).where(
            EquipmentTypeHistory.equipment_id == equip_id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentTerminalHistory).where(
            EquipmentTerminalHistory.equipment_id == equip_id  # type: ignore[arg-type]
        )
    )
    session.delete(equipment)
    session.commit()
    return EquipmentDeleteResponse(
        action="deleted",
        message="Equipment deleted successfully.",
        equipment=equipment_data,
    )


@router.get(
    "/{equipment_id}/type-history",
    response_model=EquipmentTypeHistoryListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment_type_history(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> Any:
    """
    Lista el historial de cambios de tipo del equipo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: sin acceso a la terminal del equipo.
    - 404: equipo no encontrado.
    """
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    allowed_terminal_ids = _get_allowed_terminal_ids(session, current_user)
    if allowed_terminal_ids and equipment.terminal_id not in allowed_terminal_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    history = session.exec(
        select(EquipmentTypeHistory).where(
            EquipmentTypeHistory.equipment_id == equipment_id
        )
    ).all()
    if not history:
        return EquipmentTypeHistoryListResponse(message="No records found")

    items = [EquipmentTypeHistoryRead(**h.model_dump()) for h in history]
    return EquipmentTypeHistoryListResponse(items=items)


@router.get(
    "/{equipment_id}/terminal-history",
    response_model=EquipmentTerminalHistoryListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment_terminal_history(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> Any:
    """
    Lista el historial de cambios de terminal del equipo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: sin acceso a la terminal del equipo.
    - 404: equipo no encontrado.
    """
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    allowed_terminal_ids = _get_allowed_terminal_ids(session, current_user)
    if allowed_terminal_ids and equipment.terminal_id not in allowed_terminal_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    history = session.exec(
        select(EquipmentTerminalHistory).where(
            EquipmentTerminalHistory.equipment_id == equipment_id
        )
    ).all()
    if not history:
        return EquipmentTerminalHistoryListResponse(message="No records found")

    items = [EquipmentTerminalHistoryRead(**h.model_dump()) for h in history]
    return EquipmentTerminalHistoryListResponse(items=items)


@router.get(
    "/{equipment_id}/history",
    response_model=EquipmentHistoryListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment_history(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> Any:
    """
    Lista el historial combinado de cambios de tipo y terminal.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: sin acceso a la terminal del equipo.
    - 404: equipo no encontrado.
    """
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    allowed_terminal_ids = _get_allowed_terminal_ids(session, current_user)
    if allowed_terminal_ids and equipment.terminal_id not in allowed_terminal_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    type_history = session.exec(
        select(EquipmentTypeHistory).where(
            EquipmentTypeHistory.equipment_id == equipment_id
        )
    ).all()
    terminal_history = session.exec(
        select(EquipmentTerminalHistory).where(
            EquipmentTerminalHistory.equipment_id == equipment_id
        )
    ).all()

    items: list[EquipmentHistoryEntry] = []
    user_ids: set[int] = set()
    for type_entry in type_history:
        if type_entry.changed_by_user_id:
            user_ids.add(type_entry.changed_by_user_id)
    for terminal_entry in terminal_history:
        if terminal_entry.changed_by_user_id:
            user_ids.add(terminal_entry.changed_by_user_id)
    user_name_by_id: dict[int, str] = {}
    if user_ids:
        users = session.exec(
            select(User).where(User.id.in_(user_ids))  # type: ignore[union-attr]
        ).all()
        for user in users:
            if user.id is None:
                continue
            label = (
                " ".join(filter(None, [user.name, user.last_name])).strip()
                or user.email
                or str(user.id)
            )
            user_name_by_id[user.id] = label
    for type_entry in type_history:
        items.append(
            EquipmentHistoryEntry(
                id=f"type-{type_entry.id}",
                kind="type",
                equipment_type_id=type_entry.equipment_type_id,
                terminal_id=None,
                started_at=type_entry.started_at,
                ended_at=type_entry.ended_at,
                changed_by_user_id=type_entry.changed_by_user_id,
                changed_by_user_name=user_name_by_id.get(type_entry.changed_by_user_id),
            )
        )
    for terminal_entry in terminal_history:
        items.append(
            EquipmentHistoryEntry(
                id=f"terminal-{terminal_entry.id}",
                kind="terminal",
                equipment_type_id=None,
                terminal_id=terminal_entry.terminal_id,
                started_at=terminal_entry.started_at,
                ended_at=terminal_entry.ended_at,
                changed_by_user_id=terminal_entry.changed_by_user_id,
                changed_by_user_name=user_name_by_id.get(
                    terminal_entry.changed_by_user_id
                ),
            )
        )

    if not items:
        return EquipmentHistoryListResponse(message="No records found")

    items.sort(key=lambda entry: entry.started_at)
    return EquipmentHistoryListResponse(items=items)
