import math
import re
from datetime import UTC, datetime, timedelta
from typing import assert_never, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlmodel import Session, delete, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.enums import (
    EquipmentMeasureType,
    EquipmentRole,
    EquipmentStatus,
    InspectionResponseType,
    UserType,
)
from app.models.equipment import Equipment
from app.models.equipment_calibration import EquipmentCalibration
from app.models.equipment_inspection import EquipmentInspection
from app.models.equipment_measure_spec import EquipmentMeasureSpec
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_max_error import EquipmentTypeMaxError
from app.models.equipment_type_measure import EquipmentTypeMeasure
from app.models.equipment_type_verification import (
    EquipmentTypeVerification,
)
from app.models.equipment_type_verification_item import (
    EquipmentTypeVerificationItem,
)
from app.models.equipment_verification import (
    EquipmentVerification,
    EquipmentVerificationCreate,
    EquipmentVerificationListResponse,
    EquipmentVerificationRead,
    EquipmentVerificationResponse,
    EquipmentVerificationResponseCreate,
    EquipmentVerificationResponseRead,
    EquipmentVerificationUpdate,
)
from app.models.user import User
from app.models.user_terminal import UserTerminal
from app.utils.emp_weights import get_emp
from app.utils.hydrometer import api_60f_crude
from app.utils.measurements.length import Length
from app.utils.measurements.temperature import Temperature
from app.utils.measurements.weight import Weight

router = APIRouter(
    prefix="/equipment-verifications",
    tags=["Equipment Verifications"],
)


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
    item: EquipmentTypeVerificationItem,
    response: EquipmentVerificationResponseCreate,
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
    assert_never(item.response_type)


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
            detail="El equipo no cuenta con calibracion vigente.",
        )
    if calibration_days is None or calibration_days <= 0:
        return
    calibrated_at = _as_utc(latest.calibrated_at)
    expires_at = calibrated_at + timedelta(days=calibration_days)
    if datetime.now(UTC) > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El equipo no cuenta con calibracion vigente.",
        )


def _requires_temperature_comparison(equipment_type: EquipmentType | None) -> bool:
    if equipment_type is None:
        return False
    name = equipment_type.name.strip().lower()
    return name in {
        "termometro electronico tl1",
        "termometro electronico tp7 tp9",
        "termometro de vidrio",
    }


def _is_tape_type_name(equipment_type: EquipmentType | None) -> bool:
    if equipment_type is None:
        return False
    name = equipment_type.name.strip().lower()
    return name in {
        "cinta metrica plomada fondo",
        "cinta metrica plomada vacio",
    }


def _is_hydrometer_type_name(equipment_type: EquipmentType | None) -> bool:
    if equipment_type is None:
        return False
    return equipment_type.name.strip().lower() == "hidrometro"


def _is_balance_type_name(equipment_type: EquipmentType | None) -> bool:
    if equipment_type is None:
        return False
    return equipment_type.name.strip().lower() == "balanza analitica"


def _is_kf_type_name(equipment_type: EquipmentType | None) -> bool:
    if equipment_type is None:
        return False
    return equipment_type.name.strip().lower() == "titulador karl fischer"


def _requires_tape_comparison(equipment_type: EquipmentType | None) -> bool:
    if equipment_type is None:
        return False
    if equipment_type.role != EquipmentRole.working:
        return False
    return _is_tape_type_name(equipment_type)


def _requires_balance_comparison(equipment_type: EquipmentType | None) -> bool:
    if equipment_type is None:
        return False
    if equipment_type.role != EquipmentRole.working:
        return False
    return _is_balance_type_name(equipment_type)


def _weight_to_grams(value: float, unit: str) -> float:
    unit_key = unit.strip().lower()
    if unit_key in {"g", "gram", "grams"}:
        return Weight.from_grams(value).as_grams
    if unit_key in {"mg", "milligram", "milligrams"}:
        return Weight.from_grams(value / 1000.0).as_grams
    if unit_key in {"kg", "kilogram", "kilograms"}:
        return Weight.from_kilograms(value).as_grams
    if unit_key in {"lb", "lbs", "pound", "pounds"}:
        return Weight.from_pounds(value).as_grams
    if unit_key in {"oz", "ounce", "ounces"}:
        return Weight.from_ounces(value).as_grams
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported weight unit",
    )


def _get_temperature_measure_spec(
    session: Session, equipment_id: int
) -> EquipmentMeasureSpec | None:
    return session.exec(
        select(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equipment_id,
            EquipmentMeasureSpec.measure == EquipmentMeasureType.temperature,
        )
    ).first()


def _get_length_measure_spec(
    session: Session, equipment_id: int
) -> EquipmentMeasureSpec | None:
    return session.exec(
        select(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equipment_id,
            EquipmentMeasureSpec.measure == EquipmentMeasureType.length,
        )
    ).first()


def _validate_temperature_spec(
    temperature_spec: EquipmentMeasureSpec | None, reading_c: float
) -> None:
    if not temperature_spec:
        return
    if (
        temperature_spec.min_value is not None
        and reading_c < temperature_spec.min_value
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La lectura del equipo esta por debajo del minimo permitido "
                f"({temperature_spec.min_value:.3f} C)"
            ),
        )
    if (
        temperature_spec.max_value is not None
        and reading_c > temperature_spec.max_value
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La lectura del equipo esta por encima del maximo permitido "
                f"({temperature_spec.max_value:.3f} C)"
            ),
        )
    if (
        temperature_spec.resolution is not None
        and temperature_spec.resolution > 0
        and not _matches_resolution(
            reading_c,
            temperature_spec.resolution,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La lectura del equipo no coincide con la resolucion "
                f"({temperature_spec.resolution:.6g} C)"
            ),
        )


def _validate_length_spec(
    length_spec: EquipmentMeasureSpec | None, reading_mm: float
) -> None:
    if not length_spec:
        return
    if length_spec.min_value is not None and reading_mm < length_spec.min_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La lectura del equipo esta por debajo del minimo permitido "
                f"({length_spec.min_value:.3f} mm)"
            ),
        )
    if length_spec.max_value is not None and reading_mm > length_spec.max_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La lectura del equipo esta por encima del maximo permitido "
                f"({length_spec.max_value:.3f} mm)"
            ),
        )
    if (
        length_spec.resolution is not None
        and length_spec.resolution > 0
        and not _matches_resolution(reading_mm, length_spec.resolution)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La lectura del equipo no coincide con la resolucion "
                f"({length_spec.resolution:.6g} mm)"
            ),
        )


def _parse_monthly_readings_from_notes(
    notes: str | None,
) -> dict[str, float | str] | None:
    if not notes:
        return None
    text = str(notes)
    lower_text = text.lower()
    if (
        "alto equipo" not in lower_text
        and "medio equipo" not in lower_text
        and "bajo equipo" not in lower_text
    ):
        return None

    def _extract(label: str) -> tuple[float | None, str | None]:
        match = re.search(
            rf"{label}\s*:\s*([-+]?\d*[.,]?\d+)\s*([a-zA-Z])?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return None, None
        value = float(match.group(1).replace(",", "."))
        unit = match.group(2)
        return value, unit

    alto_equipo, alto_unit = _extract("Alto equipo")
    alto_patron, patron_unit = _extract("Alto patron")
    medio_equipo, _ = _extract("Medio equipo")
    medio_patron, _ = _extract("Medio patron")
    bajo_equipo, _ = _extract("Bajo equipo")
    bajo_patron, _ = _extract("Bajo patron")

    if any(
        val is None
        for val in [
            alto_equipo,
            alto_patron,
            medio_equipo,
            medio_patron,
            bajo_equipo,
            bajo_patron,
        ]
    ):
        return None

    alto_equipo = cast(float, alto_equipo)
    alto_patron = cast(float, alto_patron)
    medio_equipo = cast(float, medio_equipo)
    medio_patron = cast(float, medio_patron)
    bajo_equipo = cast(float, bajo_equipo)
    bajo_patron = cast(float, bajo_patron)

    return {
        "reading_under_test_high_value": alto_equipo,
        "reading_under_test_mid_value": medio_equipo,
        "reading_under_test_low_value": bajo_equipo,
        "reference_reading_high_value": alto_patron,
        "reference_reading_mid_value": medio_patron,
        "reference_reading_low_value": bajo_patron,
        "reading_under_test_unit": (alto_unit or "").lower(),
        "reference_reading_unit": (patron_unit or "").lower(),
    }


def _require_id(value: int | None, label: str) -> int:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{label} has no ID",
        )
    return value


def _require_float(value: float | None, label: str) -> float:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} is required",
        )
    return float(value)


def _require_str(value: str | None, label: str) -> str:
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} is required",
        )
    return value


def _has_temperature_measure(session: Session, equipment_type_id: int) -> bool:
    return (
        session.exec(
            select(EquipmentTypeMeasure.id).where(
                EquipmentTypeMeasure.equipment_type_id == equipment_type_id,
                EquipmentTypeMeasure.measure == EquipmentMeasureType.temperature,
            )
        ).first()
        is not None
    )


def _has_length_measure(session: Session, equipment_type_id: int) -> bool:
    return (
        session.exec(
            select(EquipmentTypeMeasure.id).where(
                EquipmentTypeMeasure.equipment_type_id == equipment_type_id,
                EquipmentTypeMeasure.measure == EquipmentMeasureType.length,
            )
        ).first()
        is not None
    )


def _has_approved_daily_inspection(
    session: Session,
    equipment_id: int,
    day_start: datetime,
    day_end: datetime,
) -> bool:
    return (
        session.exec(
            select(EquipmentInspection.id).where(
                EquipmentInspection.equipment_id == equipment_id,
                EquipmentInspection.inspected_at >= day_start,
                EquipmentInspection.inspected_at < day_end,
                EquipmentInspection.is_ok == True,  # noqa: E712
            )
        ).first()
        is not None
    )


def _temperature_to_celsius(value: float, unit: str) -> float:
    key = unit.strip().lower()
    if key in {"c", "celsius"}:
        return Temperature.from_celsius(value).as_celsius
    if key in {"f", "fahrenheit"}:
        return Temperature.from_fahrenheit(value).as_celsius
    if key in {"k", "kelvin"}:
        return Temperature.from_kelvin(value).as_celsius
    if key in {"r", "rankine"}:
        return Temperature.from_rankine(value).as_celsius
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported temperature unit",
    )


def _length_to_millimeters(value: float, unit: str) -> float:
    key = unit.strip().lower()
    if key in {"mm", "millimeter", "millimeters"}:
        return Length.from_millimeters(value).as_millimeters
    if key in {"cm", "centimeter", "centimeters"}:
        return Length.from_centimeters(value).as_millimeters
    if key in {"m", "meter", "meters"}:
        return Length.from_meters(value).as_millimeters
    if key in {"in", "inch", "inches"}:
        return Length.from_inches(value).as_millimeters
    if key in {"ft", "foot", "feet"}:
        return Length.from_feet(value).as_millimeters
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported length unit",
    )


def _collect_two_or_three_readings(
    first: float | None,
    second: float | None,
    third: float | None,
    label: str,
) -> list[float]:
    if first is None or second is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se requieren al menos dos lecturas para {label}.",
        )
    readings = [float(first), float(second)]
    if third is None:
        if not math.isclose(readings[0], readings[1], rel_tol=1e-9, abs_tol=1e-9):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(f"Cuando {label} tenga solo dos lecturas, deben ser iguales."),
            )
        return readings
    readings.append(float(third))
    return readings


def _matches_resolution(value: float, resolution: float) -> bool:
    if resolution <= 0:
        return True
    quotient = value / resolution
    return math.isclose(quotient, round(quotient), rel_tol=1e-9, abs_tol=1e-9)


@router.post(
    "/equipment/{equipment_id}",
    response_model=EquipmentVerificationRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_400_BAD_REQUEST: {"description": "Solicitud inválida"},
    },
)
def create_equipment_verification(
    equipment_id: int,
    payload: EquipmentVerificationCreate,
    replace_existing: bool = Query(
        False,
        alias="replace_existing",
        description="Si es `true`, reemplaza la verificación abierta existente.",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> EquipmentVerificationRead:
    """
    Crea una verificación para un equipo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Parámetros:
    - `replace_existing`: si es `true`, reemplaza la verificación abierta del día.
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
    equipment_db_id = _require_id(equipment.id, "Equipment")

    verification_type_id = payload.verification_type_id
    verification_type: EquipmentTypeVerification | None = None
    if verification_type_id is None:
        verification_types = session.exec(
            select(EquipmentTypeVerification).where(
                EquipmentTypeVerification.equipment_type_id
                == equipment.equipment_type_id,
                EquipmentTypeVerification.is_active == True,  # noqa: E712
            )
        ).all()
        if len(verification_types) == 1 and verification_types[0].id is not None:
            verification_type_id = verification_types[0].id
            verification_type = verification_types[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="verification_type_id is required for this equipment type",
            )
    else:
        verification_type = session.get(EquipmentTypeVerification, verification_type_id)
        if (
            not verification_type
            or verification_type.equipment_type_id != equipment.equipment_type_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification_type_id for this equipment type",
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
        select(EquipmentTypeVerificationItem).where(
            EquipmentTypeVerificationItem.equipment_type_id
            == equipment.equipment_type_id,
            EquipmentTypeVerificationItem.verification_type_id == verification_type_id,
        )
    ).all()
    items_by_id = {item.id: item for item in items if item.id is not None}
    required_ids = {item.id for item in items if item.is_required}

    response_item_ids = [r.verification_item_id for r in payload.responses]
    if len(response_item_ids) != len(set(response_item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate verification_item_id in responses",
        )
    if not required_ids.issubset(set(response_item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required verification items",
        )

    evaluated_responses: list[
        tuple[EquipmentVerificationResponseCreate, bool | None]
    ] = []
    for response in payload.responses:
        if response.verification_item_id not in items_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification_item_id for this equipment type",
            )
        item = items_by_id[response.verification_item_id]
        if response.response_type != item.response_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Response type does not match verification item type",
            )
        _validate_response(
            response.response_type,
            response.value_bool,
            response.value_text,
            response.value_number,
        )
        evaluated_responses.append((response, _evaluate_response(item, response)))

    verified_at = (
        _as_utc(payload.verified_at) if payload.verified_at else datetime.now(UTC)
    )
    day_start = datetime(
        verified_at.year,
        verified_at.month,
        verified_at.day,
        tzinfo=UTC,
    )
    day_end = day_start + timedelta(days=1)
    equipment_type = session.get(EquipmentType, equipment.equipment_type_id)
    equipment_type_id = equipment_type.id if equipment_type else None
    applies_temperature_comparison_rule = (
        equipment_type is not None
        and _requires_temperature_comparison(equipment_type)
        and equipment_type_id is not None
        and _has_temperature_measure(session, equipment_type_id)
    )
    applies_tape_comparison_rule = (
        equipment_type is not None
        and _requires_tape_comparison(equipment_type)
        and equipment_type_id is not None
        and _has_length_measure(session, equipment_type_id)
    )
    applies_balance_comparison_rule = (
        equipment_type is not None and _requires_balance_comparison(equipment_type)
    )
    applies_kf_verification_rule = equipment_type is not None and _is_kf_type_name(
        equipment_type
    )
    applies_kf_verification_rule = equipment_type is not None and _is_kf_type_name(
        equipment_type
    )
    applies_hydrometer_comparison_rule = (
        equipment_type is not None
        and _is_hydrometer_type_name(equipment_type)
        and equipment_type.role == EquipmentRole.working
        and bool(verification_type and int(verification_type.frequency_days) == 30)
    )
    applies_comparison_rule = (
        applies_temperature_comparison_rule
        or applies_tape_comparison_rule
        or applies_balance_comparison_rule
        or applies_hydrometer_comparison_rule
    )
    is_monthly = bool(verification_type and int(verification_type.frequency_days) == 30)
    comparison_ok = True
    comparison_message: str | None = None
    use_unit_values = False
    use_f_values = False
    delta_c = 0.0
    tape_under_readings: list[float] = []
    tape_ref_readings: list[float] = []
    tape_under_unit = ""
    tape_ref_unit = ""
    tape_avg_under_mm = 0.0
    tape_avg_ref_mm = 0.0
    tape_diff_mm = 0.0
    balance_under_g = 0.0
    balance_ref_g = 0.0
    balance_diff_g = 0.0
    balance_max_error_g = None
    kf_factor_1 = 0.0
    kf_factor_2 = 0.0
    kf_factor_avg = 0.0
    kf_error_rel = 0.0
    kf_factor_1 = 0.0
    kf_factor_2 = 0.0
    kf_factor_avg = 0.0
    kf_error_rel = 0.0
    if applies_comparison_rule or applies_kf_verification_rule:
        if payload.reference_equipment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reference_equipment_id is required for this verification",
            )
        use_unit_values = bool(
            payload.reading_under_test_value is not None
            and payload.reference_reading_value is not None
            and payload.reading_under_test_unit
            and payload.reference_reading_unit
        )
        use_f_values = bool(
            payload.reading_under_test_f is not None
            and payload.reference_reading_f is not None
        )
        if (
            applies_temperature_comparison_rule
            and not is_monthly
            and not use_unit_values
            and not use_f_values
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "reading_under_test_value/reference_reading_value with units "
                    "or reading_under_test_f/reference_reading_f are required for this verification"
                ),
            )
        reference_equipment = session.get(Equipment, payload.reference_equipment_id)
        if not reference_equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference equipment not found",
            )
        reference_equipment_id = _require_id(
            reference_equipment.id, "Reference equipment"
        )
        if reference_equipment_id == equipment_db_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be different from equipment under test",
            )
        if reference_equipment.status != EquipmentStatus.in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be in use",
            )
        if reference_equipment.terminal_id != equipment.terminal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must belong to the same terminal",
            )
        reference_type = session.get(
            EquipmentType, reference_equipment.equipment_type_id
        )
        if reference_type is None or reference_type.id is None or (
            reference_type.role != EquipmentRole.reference
            and not applies_kf_verification_rule
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be a reference equipment",
            )
        reference_type_id = reference_type.id
        if applies_temperature_comparison_rule and not _has_temperature_measure(
            session, reference_type_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be a temperature reference equipment",
            )
        if applies_hydrometer_comparison_rule:
            if not _is_hydrometer_type_name(reference_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference equipment must be a hydrometer reference equipment",
                )
        if applies_tape_comparison_rule:
            if not _is_tape_type_name(reference_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference equipment must be a tape reference equipment",
                )
            if not _has_length_measure(session, reference_type_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference equipment must support length measure",
                )
        if applies_balance_comparison_rule:
            if (
                reference_type is None
                or not reference_type.name.strip().lower().startswith("pesa")
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference equipment must be a weight (pesa) reference equipment",
                )
            if (
                reference_equipment.nominal_mass_value is None
                or not reference_equipment.nominal_mass_unit
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference weight must have nominal mass defined",
                )
        equipment_inspection_days = (
            equipment.inspection_days_override
            if equipment.inspection_days_override is not None
            else (equipment_type.inspection_days if equipment_type else 0)
        )
        reference_inspection_days = (
            reference_equipment.inspection_days_override
            if reference_equipment.inspection_days_override is not None
            else (reference_type.inspection_days if reference_type else 0)
        )
        requires_equipment_inspection = (equipment_inspection_days or 0) > 0
        requires_reference_inspection = (reference_inspection_days or 0) > 0
        has_daily_inspection_equipment = (
            _has_approved_daily_inspection(
                session=session,
                    equipment_id=equipment_db_id,
                    day_start=day_start,
                    day_end=day_end,
                )
            if requires_equipment_inspection
            else True
        )
        has_daily_inspection_reference = (
            _has_approved_daily_inspection(
                session=session,
                    equipment_id=reference_equipment_id,
                    day_start=day_start,
                    day_end=day_end,
                )
            if requires_reference_inspection
            else True
        )
        if not has_daily_inspection_equipment or not has_daily_inspection_reference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Both equipment and reference equipment must have an approved daily "
                    "inspection for the verification date"
                ),
            )
        is_monthly = bool(
            verification_type and int(verification_type.frequency_days) == 30
        )
        if applies_hydrometer_comparison_rule:
            if (
                payload.reading_under_test_value is None
                or payload.reference_reading_value is None
                or payload.reading_under_test_f is None
                or payload.reference_reading_f is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Hydrometer working/reference readings and thermometer "
                        "readings (in F) are required for this verification"
                    ),
                )
            try:
                work_api60 = api_60f_crude(
                    _require_float(
                        payload.reading_under_test_f, "reading_under_test_f"
                    ),
                    _require_float(
                        payload.reading_under_test_value, "reading_under_test_value"
                    ),
                )
                ref_api60 = api_60f_crude(
                    _require_float(
                        payload.reference_reading_f, "reference_reading_f"
                    ),
                    _require_float(
                        payload.reference_reading_value, "reference_reading_value"
                    ),
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            diff_api = work_api60 - ref_api60
            comparison_ok = -0.5 <= diff_api <= 0.5
            if not comparison_ok:
                comparison_message = (
                    "Diferencia API a 60F fuera del rango permitido (-0.5 a 0.5)."
                )
        elif applies_temperature_comparison_rule:
            temperature_spec = _get_temperature_measure_spec(session, equipment_db_id)
            if is_monthly:
                try:
                    under_unit = _require_str(
                        payload.reading_under_test_unit, "reading_under_test_unit"
                    )
                    ref_unit = _require_str(
                        payload.reference_reading_unit, "reference_reading_unit"
                    )
                    readings = [
                        (
                            "Alto",
                            _require_float(
                                payload.reading_under_test_high_value,
                                "reading_under_test_high_value",
                            ),
                            _require_float(
                                payload.reference_reading_high_value,
                                "reference_reading_high_value",
                            ),
                        ),
                        (
                            "Medio",
                            _require_float(
                                payload.reading_under_test_mid_value,
                                "reading_under_test_mid_value",
                            ),
                            _require_float(
                                payload.reference_reading_mid_value,
                                "reference_reading_mid_value",
                            ),
                        ),
                        (
                            "Bajo",
                            _require_float(
                                payload.reading_under_test_low_value,
                                "reading_under_test_low_value",
                            ),
                            _require_float(
                                payload.reference_reading_low_value,
                                "reference_reading_low_value",
                            ),
                        ),
                    ]
                    diffs: list[tuple[str, float, float, float]] = []
                    for label, under_val, ref_val in readings:
                        reading_under_test_c = _temperature_to_celsius(
                            under_val, under_unit
                        )
                        reference_reading_c = _temperature_to_celsius(
                            ref_val, ref_unit
                        )
                        _validate_temperature_spec(
                            temperature_spec, reading_under_test_c
                        )
                        delta_c = abs(reading_under_test_c - reference_reading_c)
                        diffs.append((label, under_val, ref_val, delta_c))
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(exc),
                    ) from exc
                max_delta_c = 0.5 * 5.0 / 9.0
                comparison_ok = all(
                    delta_c <= max_delta_c for _, _, _, delta_c in diffs
                )
                if not comparison_ok:
                    comparison_message = (
                        "Difference between readings exceeds maximum 0.5 F."
                    )
            else:
                if not is_monthly and not use_unit_values and not use_f_values:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "reading_under_test_value/reference_reading_value with units "
                            "or reading_under_test_f/reference_reading_f are required for this verification"
                        ),
                    )
                if use_unit_values:
                    try:
                        under_unit = _require_str(
                            payload.reading_under_test_unit,
                            "reading_under_test_unit",
                        )
                        ref_unit = _require_str(
                            payload.reference_reading_unit,
                            "reference_reading_unit",
                        )
                        reading_under_test_c = _temperature_to_celsius(
                            _require_float(
                                payload.reading_under_test_value,
                                "reading_under_test_value",
                            ),
                            under_unit,
                        )
                        reference_reading_c = _temperature_to_celsius(
                            _require_float(
                                payload.reference_reading_value,
                                "reference_reading_value",
                            ),
                            ref_unit,
                        )
                    except ValueError as exc:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(exc),
                        ) from exc
                else:
                    reading_under_test_c = _temperature_to_celsius(
                        _require_float(
                            payload.reading_under_test_f, "reading_under_test_f"
                        ),
                        "f",
                    )
                    reference_reading_c = _temperature_to_celsius(
                        _require_float(
                            payload.reference_reading_f, "reference_reading_f"
                        ),
                        "f",
                    )
                _validate_temperature_spec(temperature_spec, reading_under_test_c)
                delta_c = abs(reading_under_test_c - reference_reading_c)
                max_delta_c = 0.5 * 5.0 / 9.0
                comparison_ok = delta_c <= max_delta_c
                if not comparison_ok:
                    comparison_message = (
                        f"Difference between readings is {delta_c:.3f} C and exceeds maximum "
                        f"{max_delta_c:.3f} C."
                    )
        elif applies_tape_comparison_rule:
            if (
                not payload.reading_under_test_unit
                or not payload.reference_reading_unit
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Units are required for tape verification",
                )
            tape_under_unit = _require_str(
                payload.reading_under_test_unit, "reading_under_test_unit"
            )
            tape_ref_unit = _require_str(
                payload.reference_reading_unit, "reference_reading_unit"
            )
            tape_under_readings = _collect_two_or_three_readings(
                payload.reading_under_test_high_value,
                payload.reading_under_test_mid_value,
                payload.reading_under_test_low_value,
                "el equipo de trabajo",
            )
            tape_ref_readings = _collect_two_or_three_readings(
                payload.reference_reading_high_value,
                payload.reference_reading_mid_value,
                payload.reference_reading_low_value,
                "el equipo patron",
            )
            length_spec = _get_length_measure_spec(session, equipment_db_id)
            tape_under_mm: list[float] = []
            for reading in tape_under_readings:
                reading_mm = _length_to_millimeters(reading, tape_under_unit)
                _validate_length_spec(length_spec, reading_mm)
                tape_under_mm.append(reading_mm)
            tape_ref_mm = [
                _length_to_millimeters(reading, tape_ref_unit)
                for reading in tape_ref_readings
            ]
            tape_avg_under_mm = sum(tape_under_mm) / len(tape_under_mm)
            tape_avg_ref_mm = sum(tape_ref_mm) / len(tape_ref_mm)
            tape_diff_mm = tape_avg_ref_mm - tape_avg_under_mm
            comparison_ok = abs(tape_diff_mm) < 2.0
            if not comparison_ok:
                comparison_message = (
                    f"Diferencia promedio de cinta {tape_diff_mm:.3f} mm fuera del limite "
                    f"(< 2.000 mm)."
                )
        elif applies_balance_comparison_rule:
            if (
                payload.reading_under_test_value is None
                or not payload.reading_under_test_unit
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="reading_under_test_value and reading_under_test_unit are required for balance verification",
                )
            if (
                reference_equipment.nominal_mass_value is None
                or not reference_equipment.nominal_mass_unit
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference weight must have nominal mass defined",
                )
            try:
                balance_under_g = _weight_to_grams(
                    float(payload.reading_under_test_value),
                    payload.reading_under_test_unit,
                )
                balance_ref_g = _weight_to_grams(
                    float(reference_equipment.nominal_mass_value),
                    reference_equipment.nominal_mass_unit,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            balance_diff_g = balance_ref_g - balance_under_g
            balance_max_error_g = reference_equipment.emp_value
            if (
                balance_max_error_g is None
                and reference_equipment.weight_class
                and reference_equipment.nominal_mass_value is not None
                and reference_equipment.nominal_mass_unit
            ):
                try:
                    balance_max_error_g = get_emp(
                        reference_equipment.weight_class,
                        reference_equipment.nominal_mass_value,
                        reference_equipment.nominal_mass_unit,
                    )
                except ValueError:
                    balance_max_error_g = None
            if balance_max_error_g is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se encontro el EMP de la pesa patron.",
                )
            comparison_ok = abs(balance_diff_g) <= balance_max_error_g
            if not comparison_ok:
                comparison_message = (
                    "Diferencia entre pesa y balanza supera el error maximo permitido."
                )
    if applies_kf_verification_rule:
        if payload.reference_equipment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance is required for Karl Fischer standardization",
            )
        kf_reference = session.get(Equipment, payload.reference_equipment_id)
        if not kf_reference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference balance not found",
            )
        if kf_reference.id == equipment.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must be different from equipment under test",
            )
        if kf_reference.status != EquipmentStatus.in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must be in use",
            )
        if kf_reference.terminal_id != equipment.terminal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must belong to the same terminal",
            )
        kf_reference_type = session.get(EquipmentType, kf_reference.equipment_type_id)
        if not _is_balance_type_name(kf_reference_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be a balance",
            )
        if (
            payload.kf_weight_1 is None
            or payload.kf_volume_1 is None
            or payload.kf_weight_2 is None
            or payload.kf_volume_2 is None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF weights and volumes are required",
            )
        if payload.kf_volume_1 <= 0 or payload.kf_volume_2 <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF volumes must be greater than zero",
            )
        kf_factor_1 = float(payload.kf_weight_1) / float(payload.kf_volume_1)
        kf_factor_2 = float(payload.kf_weight_2) / float(payload.kf_volume_2)
        kf_factor_avg = (kf_factor_1 + kf_factor_2) / 2.0
        if kf_factor_avg == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF average factor cannot be zero",
            )
        kf_error_rel = abs(kf_factor_1 - kf_factor_2) / kf_factor_avg * 100.0
        factors_ok = 4.5 <= kf_factor_1 <= 5.5 and 4.5 <= kf_factor_2 <= 5.5
        rel_ok = kf_error_rel < 2.0
        comparison_ok = factors_ok and rel_ok
        if not comparison_ok:
            comparison_message = "Factor fuera de 4.5-5.5 o error relativo >= 2%."
    if applies_kf_verification_rule:
        if payload.reference_equipment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reference_equipment_id is required for Karl Fischer verification",
            )
        kf_reference = session.get(Equipment, payload.reference_equipment_id)
        if not kf_reference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference balance not found",
            )
        if kf_reference.id == equipment.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must be different from equipment under test",
            )
        if kf_reference.status != EquipmentStatus.in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must be in use",
            )
        if kf_reference.terminal_id != equipment.terminal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must belong to the same terminal",
            )
        kf_reference_type = session.get(EquipmentType, kf_reference.equipment_type_id)
        if not _is_balance_type_name(kf_reference_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be a balance",
            )
        if (
            payload.kf_weight_1 is None
            or payload.kf_volume_1 is None
            or payload.kf_weight_2 is None
            or payload.kf_volume_2 is None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF weights and volumes are required",
            )
        if payload.kf_volume_1 <= 0 or payload.kf_volume_2 <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF volumes must be greater than zero",
            )
        kf_factor_1 = float(payload.kf_weight_1) / float(payload.kf_volume_1)
        kf_factor_2 = float(payload.kf_weight_2) / float(payload.kf_volume_2)
        kf_factor_avg = (kf_factor_1 + kf_factor_2) / 2.0
        if kf_factor_avg == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF average factor cannot be zero",
            )
        kf_error_rel = abs(kf_factor_1 - kf_factor_2) / kf_factor_avg * 100.0
        factors_ok = 4.5 <= kf_factor_1 <= 5.5 and 4.5 <= kf_factor_2 <= 5.5
        rel_ok = kf_error_rel < 2.0
        comparison_ok = factors_ok and rel_ok
        if not comparison_ok:
            comparison_message = "Factor fuera de 4.5-5.5 o error relativo >= 2%."
    if applies_kf_verification_rule:
        if payload.reference_equipment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reference_equipment_id is required for Karl Fischer verification",
            )
        kf_reference = session.get(Equipment, payload.reference_equipment_id)
        if not kf_reference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference balance not found",
            )
        if kf_reference.id == equipment.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must be different from equipment under test",
            )
        if kf_reference.status != EquipmentStatus.in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must be in use",
            )
        if kf_reference.terminal_id != equipment.terminal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference balance must belong to the same terminal",
            )
        kf_reference_type = session.get(EquipmentType, kf_reference.equipment_type_id)
        if not _is_balance_type_name(kf_reference_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be a balance",
            )
        if (
            payload.kf_weight_1 is None
            or payload.kf_volume_1 is None
            or payload.kf_weight_2 is None
            or payload.kf_volume_2 is None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF weights and volumes are required",
            )
        if payload.kf_volume_1 <= 0 or payload.kf_volume_2 <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF volumes must be greater than zero",
            )
        kf_factor_1 = float(payload.kf_weight_1) / float(payload.kf_volume_1)
        kf_factor_2 = float(payload.kf_weight_2) / float(payload.kf_volume_2)
        kf_factor_avg = (kf_factor_1 + kf_factor_2) / 2.0
        if kf_factor_avg == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KF average factor cannot be zero",
            )
        kf_error_rel = abs(kf_factor_1 - kf_factor_2) / kf_factor_avg * 100.0
        factors_ok = 4.5 <= kf_factor_1 <= 5.5 and 4.5 <= kf_factor_2 <= 5.5
        rel_ok = kf_error_rel < 2.0
        comparison_ok = factors_ok and rel_ok
        if not comparison_ok:
            comparison_message = "Factor fuera de 4.5-5.5 o error relativo >= 2%."
    existing_same_day = session.exec(
        select(EquipmentVerification).where(
            EquipmentVerification.equipment_id == equipment.id,
            EquipmentVerification.verification_type_id == verification_type_id,
            EquipmentVerification.verified_at >= day_start,
            EquipmentVerification.verified_at < day_end,
        )
    ).first()
    if existing_same_day:
        if not replace_existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya se realizó una verificación hoy. ¿Deseas reemplazarla?",
            )
        existing_id = existing_same_day.id
        if existing_id is not None:
            session.exec(
                delete(EquipmentVerificationResponse).where(
                    EquipmentVerificationResponse.verification_id == existing_id  # type: ignore[arg-type]
                )
            )
            session.exec(
                delete(EquipmentVerification).where(
                    EquipmentVerification.id == existing_id  # type: ignore[arg-type]
                )
            )
            session.commit()

    verification_ok = (
        all(is_ok is True for _, is_ok in evaluated_responses) and comparison_ok
    )
    notes = payload.notes
    if applies_comparison_rule or applies_kf_verification_rule:
        equipment_type_name = equipment_type.name if equipment_type else "Equipo"
        reference_equipment = cast(Equipment, reference_equipment)
        if applies_temperature_comparison_rule and is_monthly:
            try:
                under_unit = _require_str(
                    payload.reading_under_test_unit, "reading_under_test_unit"
                )
                ref_unit = _require_str(
                    payload.reference_reading_unit, "reference_reading_unit"
                )
                under_high = _require_float(
                    payload.reading_under_test_high_value,
                    "reading_under_test_high_value",
                )
                under_mid = _require_float(
                    payload.reading_under_test_mid_value,
                    "reading_under_test_mid_value",
                )
                under_low = _require_float(
                    payload.reading_under_test_low_value,
                    "reading_under_test_low_value",
                )
                ref_high = _require_float(
                    payload.reference_reading_high_value,
                    "reference_reading_high_value",
                )
                ref_mid = _require_float(
                    payload.reference_reading_mid_value,
                    "reference_reading_mid_value",
                )
                ref_low = _require_float(
                    payload.reference_reading_low_value,
                    "reference_reading_low_value",
                )
                delta_high = abs(
                    _temperature_to_celsius(under_high, under_unit)
                    - _temperature_to_celsius(ref_high, ref_unit)
                )
                delta_mid = abs(
                    _temperature_to_celsius(under_mid, under_unit)
                    - _temperature_to_celsius(ref_mid, ref_unit)
                )
                delta_low = abs(
                    _temperature_to_celsius(under_low, under_unit)
                    - _temperature_to_celsius(ref_low, ref_unit)
                )
            except (TypeError, ValueError):
                under_unit = payload.reading_under_test_unit or ""
                ref_unit = payload.reference_reading_unit or ""
                under_high = under_mid = under_low = 0.0
                ref_high = ref_mid = ref_low = 0.0
                delta_high = delta_mid = delta_low = 0.0
            comparison_note = (
                f"Comparacion mensual {equipment_type_name} | "
                f"Patron ID: {payload.reference_equipment_id} | "
                f"Alto equipo: {under_high} {under_unit} | "
                f"Alto patron: {ref_high} {ref_unit} | "
                f"Dif Alto: {delta_high:.3f} C | "
                f"Medio equipo: {under_mid} {under_unit} | "
                f"Medio patron: {ref_mid} {ref_unit} | "
                f"Dif Medio: {delta_mid:.3f} C | "
                f"Bajo equipo: {under_low} {under_unit} | "
                f"Bajo patron: {ref_low} {ref_unit} | "
                f"Dif Bajo: {delta_low:.3f} C"
            )
        elif applies_temperature_comparison_rule:
            if use_unit_values:
                reading_under_test_label = f"{payload.reading_under_test_value} {payload.reading_under_test_unit}"
                reference_reading_label = f"{payload.reference_reading_value} {payload.reference_reading_unit}"
            else:
                reading_under_test_label = f"{payload.reading_under_test_f} F"
                reference_reading_label = f"{payload.reference_reading_f} F"
            comparison_note = (
                f"Comparacion {equipment_type_name} | "
                f"Patron ID: {payload.reference_equipment_id} | "
                f"Lectura equipo: {reading_under_test_label} | "
                f"Lectura patron: {reference_reading_label} | "
                f"Diferencia: {delta_c:.3f} C"
            )
        elif applies_balance_comparison_rule:
            ref_unit = reference_equipment.nominal_mass_unit or "g"
            under_unit = payload.reading_under_test_unit or "g"
            comparison_note = (
                f"Comparacion balanza {equipment_type_name} | "
                f"Patron ID: {payload.reference_equipment_id} | "
                f"Pesa: {reference_equipment.nominal_mass_value} {ref_unit} | "
                f"Lectura balanza: {payload.reading_under_test_value} {under_unit} | "
                f"Diferencia (Pesa-Balanza): {balance_diff_g:.6f} g | "
                f"Criterio: |Diferencia| <= {balance_max_error_g:.6g} g"
            )
        elif applies_kf_verification_rule:
            comparison_note = (
                "[[KF_DATA]] Verificacion Karl Fischer | "
                f"Balanza ID: {payload.reference_equipment_id} | "
                f"Peso1: {payload.kf_weight_1} mg | "
                f"Volumen1: {payload.kf_volume_1} mL | "
                f"Factor1: {kf_factor_1:.6f} | "
                f"Peso2: {payload.kf_weight_2} mg | "
                f"Volumen2: {payload.kf_volume_2} mL | "
                f"Factor2: {kf_factor_2:.6f} | "
                f"Factor promedio: {kf_factor_avg:.6f} | "
                f"Error relativo: {kf_error_rel:.3f}% | "
                "Criterio: Factores 4.5-5.5 mg/mL y Error < 2%"
            )
        else:
            work_values = ", ".join(f"{value:g}" for value in tape_under_readings)
            ref_values = ", ".join(f"{value:g}" for value in tape_ref_readings)
            comparison_note = (
                f"Comparacion cinta {equipment_type_name} | "
                f"Patron ID: {payload.reference_equipment_id} | "
                f"Lecturas equipo: [{work_values}] {tape_under_unit} | "
                f"Promedio equipo: {tape_avg_under_mm:.3f} mm | "
                f"Lecturas patron: [{ref_values}] {tape_ref_unit} | "
                f"Promedio patron: {tape_avg_ref_mm:.3f} mm | "
                f"Diferencia (Patron-Equipo): {tape_diff_mm:.3f} mm | "
                "Criterio: |Diferencia| < 2.000 mm"
            )
        notes = (
            f"{payload.notes}\n{comparison_note}" if payload.notes else comparison_note
        )
    verification = EquipmentVerification(
        equipment_id=equipment_db_id,
        verification_type_id=verification_type_id,
        verified_at=verified_at,
        created_by_user_id=current_user.id,
        notes=notes,
        is_ok=verification_ok,
    )
    session.add(verification)
    session.commit()
    session.refresh(verification)
    verification_db_id = _require_id(verification.id, "Verification")

    for response, is_ok in evaluated_responses:
        session.add(
            EquipmentVerificationResponse(
                verification_id=verification_db_id,
                verification_item_id=response.verification_item_id,
                response_type=response.response_type,
                value_bool=response.value_bool,
                value_text=response.value_text,
                value_number=response.value_number,
                is_ok=is_ok,
            )
        )
    session.commit()

    responses = session.exec(
        select(EquipmentVerificationResponse).where(
            EquipmentVerificationResponse.verification_id == verification_db_id
        )
    ).all()
    message: str | None = None
    if verification_ok is False:
        equipment.status = EquipmentStatus.needs_review
        session.add(equipment)
        session.commit()
        message = (
            comparison_message
            or "Verification failed. Equipment status set to needs_review."
        )
    if verification_ok is True:
        equipment.status = EquipmentStatus.in_use
        session.add(equipment)
        session.commit()
    verification_read = EquipmentVerificationRead.model_validate(
        verification, from_attributes=True
    )
    verification_read.responses = [
        EquipmentVerificationResponseRead.model_validate(r, from_attributes=True)
        for r in responses
    ]
    monthly = _parse_monthly_readings_from_notes(verification_read.notes)
    if monthly:
        for key, value in monthly.items():
            setattr(verification_read, key, value)
    verification_read.message = message
    return verification_read


@router.patch(
    "/{verification_id}",
    response_model=EquipmentVerificationRead,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_equipment_verification(
    verification_id: int,
    payload: EquipmentVerificationUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentVerificationRead:
    """
    Actualiza una verificación existente por ID.

    Permisos: `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    verification = session.get(EquipmentVerification, verification_id)
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found",
        )

    equipment = session.get(Equipment, verification.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    verification_db_id = _require_id(verification.id, "Verification")
    equipment_db_id = _require_id(equipment.id, "Equipment")

    verification_type_id = (
        payload.verification_type_id or verification.verification_type_id
    )
    verification_type = session.get(EquipmentTypeVerification, verification_type_id)
    if (
        not verification_type
        or verification_type.equipment_type_id != equipment.equipment_type_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification_type_id for this equipment type",
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
        select(EquipmentTypeVerificationItem).where(
            EquipmentTypeVerificationItem.equipment_type_id
            == equipment.equipment_type_id,
            EquipmentTypeVerificationItem.verification_type_id == verification_type_id,
        )
    ).all()
    items_by_id = {item.id: item for item in items if item.id is not None}
    required_ids = {item.id for item in items if item.is_required}

    response_item_ids = [r.verification_item_id for r in payload.responses]
    if len(response_item_ids) != len(set(response_item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate verification_item_id in responses",
        )
    if not required_ids.issubset(set(response_item_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required verification items",
        )

    evaluated_responses: list[
        tuple[EquipmentVerificationResponseCreate, bool | None]
    ] = []
    for response in payload.responses:
        if response.verification_item_id not in items_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification_item_id for this equipment type",
            )
        item = items_by_id[response.verification_item_id]
        if response.response_type != item.response_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Response type does not match verification item type",
            )
        _validate_response(
            response.response_type,
            response.value_bool,
            response.value_text,
            response.value_number,
        )
        evaluated_responses.append((response, _evaluate_response(item, response)))

    verified_at = (
        _as_utc(payload.verified_at)
        if payload.verified_at
        else _as_utc(verification.verified_at)
    )
    day_start = datetime(
        verified_at.year,
        verified_at.month,
        verified_at.day,
        tzinfo=UTC,
    )
    day_end = day_start + timedelta(days=1)
    existing_same_day = session.exec(
        select(EquipmentVerification).where(
            EquipmentVerification.equipment_id == equipment_db_id,
            EquipmentVerification.verification_type_id == verification_type_id,
            EquipmentVerification.verified_at >= day_start,
            EquipmentVerification.verified_at < day_end,
            EquipmentVerification.id != verification_db_id,
        )
    ).first()
    if existing_same_day:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una verificación para esta fecha.",
        )

    equipment_type = session.get(EquipmentType, equipment.equipment_type_id)
    equipment_type_id = equipment_type.id if equipment_type else None
    applies_temperature_comparison_rule = (
        equipment_type is not None
        and _requires_temperature_comparison(equipment_type)
        and equipment_type_id is not None
        and _has_temperature_measure(session, equipment_type_id)
    )
    applies_tape_comparison_rule = (
        equipment_type is not None
        and _requires_tape_comparison(equipment_type)
        and equipment_type_id is not None
        and _has_length_measure(session, equipment_type_id)
    )
    applies_balance_comparison_rule = (
        equipment_type is not None and _requires_balance_comparison(equipment_type)
    )
    applies_kf_verification_rule = equipment_type is not None and _is_kf_type_name(
        equipment_type
    )
    applies_hydrometer_comparison_rule = (
        equipment_type is not None
        and _is_hydrometer_type_name(equipment_type)
        and equipment_type.role == EquipmentRole.working
        and bool(int(verification_type.frequency_days) == 30)
    )
    applies_comparison_rule = (
        applies_temperature_comparison_rule
        or applies_tape_comparison_rule
        or applies_balance_comparison_rule
        or applies_hydrometer_comparison_rule
    )
    is_monthly = bool(int(verification_type.frequency_days) == 30)
    comparison_ok = True
    comparison_message: str | None = None
    use_unit_values = False
    use_f_values = False
    delta_c = 0.0
    tape_under_readings: list[float] = []
    tape_ref_readings: list[float] = []
    tape_under_unit = ""
    tape_ref_unit = ""
    tape_avg_under_mm = 0.0
    tape_avg_ref_mm = 0.0
    tape_diff_mm = 0.0
    balance_under_g = 0.0
    balance_ref_g = 0.0
    balance_diff_g = 0.0
    balance_max_error_g = None
    kf_factor_1 = 0.0
    kf_factor_2 = 0.0
    kf_factor_avg = 0.0
    kf_error_rel = 0.0
    if applies_comparison_rule or applies_kf_verification_rule:
        if payload.reference_equipment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reference_equipment_id is required for this verification",
            )
        use_unit_values = bool(
            payload.reading_under_test_value is not None
            and payload.reference_reading_value is not None
            and payload.reading_under_test_unit
            and payload.reference_reading_unit
        )
        use_f_values = bool(
            payload.reading_under_test_f is not None
            and payload.reference_reading_f is not None
        )
        if (
            applies_temperature_comparison_rule
            and not is_monthly
            and not use_unit_values
            and not use_f_values
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "reading_under_test_value/reference_reading_value with units "
                    "or reading_under_test_f/reference_reading_f are required for this verification"
                ),
            )
        reference_equipment = session.get(Equipment, payload.reference_equipment_id)
        if not reference_equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference equipment not found",
            )
        reference_equipment_id = _require_id(
            reference_equipment.id, "Reference equipment"
        )
        if reference_equipment_id == equipment_db_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be different from equipment under test",
            )
        if reference_equipment.status != EquipmentStatus.in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be in use",
            )
        if reference_equipment.terminal_id != equipment.terminal_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must belong to the same terminal",
            )
        reference_type = session.get(
            EquipmentType, reference_equipment.equipment_type_id
        )
        if reference_type is None or reference_type.id is None or (
            reference_type.role != EquipmentRole.reference
            and not applies_kf_verification_rule
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be a reference equipment",
            )
        reference_type_id = reference_type.id
        if applies_temperature_comparison_rule and not _has_temperature_measure(
            session, reference_type_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference equipment must be a temperature reference equipment",
            )
        if applies_hydrometer_comparison_rule:
            if not _is_hydrometer_type_name(reference_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference equipment must be a hydrometer reference equipment",
                )
        if applies_tape_comparison_rule:
            if not _is_tape_type_name(reference_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference equipment must be a tape reference equipment",
                )
            if not _has_length_measure(session, reference_type_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference equipment must support length measure",
                )
        if applies_balance_comparison_rule:
            if (
                reference_type is None
                or not reference_type.name.strip().lower().startswith("pesa")
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference equipment must be a weight (pesa) reference equipment",
                )
            if (
                reference_equipment.nominal_mass_value is None
                or not reference_equipment.nominal_mass_unit
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference weight must have nominal mass defined",
                )
        equipment_inspection_days = (
            equipment.inspection_days_override
            if equipment.inspection_days_override is not None
            else (equipment_type.inspection_days if equipment_type else 0)
        )
        reference_inspection_days = (
            reference_equipment.inspection_days_override
            if reference_equipment.inspection_days_override is not None
            else (reference_type.inspection_days if reference_type else 0)
        )
        requires_equipment_inspection = (equipment_inspection_days or 0) > 0
        requires_reference_inspection = (reference_inspection_days or 0) > 0
        has_daily_inspection_equipment = (
            _has_approved_daily_inspection(
                session=session,
                    equipment_id=equipment_db_id,
                    day_start=day_start,
                    day_end=day_end,
                )
            if requires_equipment_inspection
            else True
        )
        has_daily_inspection_reference = (
            _has_approved_daily_inspection(
                session=session,
                    equipment_id=reference_equipment_id,
                    day_start=day_start,
                    day_end=day_end,
                )
            if requires_reference_inspection
            else True
        )
        if not has_daily_inspection_equipment or not has_daily_inspection_reference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Both equipment and reference equipment must have an approved daily "
                    "inspection for the verification date"
                ),
            )
        if applies_hydrometer_comparison_rule:
            if (
                payload.reading_under_test_value is None
                or payload.reference_reading_value is None
                or payload.reading_under_test_f is None
                or payload.reference_reading_f is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Hydrometer working/reference readings and thermometer "
                        "readings (in F) are required for this verification"
                    ),
                )
            try:
                work_api60 = api_60f_crude(
                    _require_float(
                        payload.reading_under_test_f, "reading_under_test_f"
                    ),
                    _require_float(
                        payload.reading_under_test_value, "reading_under_test_value"
                    ),
                )
                ref_api60 = api_60f_crude(
                    _require_float(
                        payload.reference_reading_f, "reference_reading_f"
                    ),
                    _require_float(
                        payload.reference_reading_value, "reference_reading_value"
                    ),
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            diff_api = work_api60 - ref_api60
            comparison_ok = -0.5 <= diff_api <= 0.5
            if not comparison_ok:
                comparison_message = (
                    "Diferencia API a 60F fuera del rango permitido (-0.5 a 0.5)."
                )
        elif applies_temperature_comparison_rule:
            temperature_spec = _get_temperature_measure_spec(session, equipment_db_id)
            if not temperature_spec:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Temperature measure spec is required for this equipment",
                )
            if is_monthly:
                if not (
                    payload.reading_under_test_high_value is not None
                    and payload.reading_under_test_mid_value is not None
                    and payload.reading_under_test_low_value is not None
                    and payload.reference_reading_high_value is not None
                    and payload.reference_reading_mid_value is not None
                    and payload.reference_reading_low_value is not None
                    and payload.reading_under_test_unit
                    and payload.reference_reading_unit
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "High/medium/low readings with units are required for monthly verification"
                        ),
                    )
                under_unit = _require_str(
                    payload.reading_under_test_unit, "reading_under_test_unit"
                )
                ref_unit = _require_str(
                    payload.reference_reading_unit, "reference_reading_unit"
                )
                readings = [
                    (
                        "Alto",
                        _require_float(
                            payload.reading_under_test_high_value,
                            "reading_under_test_high_value",
                        ),
                        _require_float(
                            payload.reference_reading_high_value,
                            "reference_reading_high_value",
                        ),
                    ),
                    (
                        "Medio",
                        _require_float(
                            payload.reading_under_test_mid_value,
                            "reading_under_test_mid_value",
                        ),
                        _require_float(
                            payload.reference_reading_mid_value,
                            "reference_reading_mid_value",
                        ),
                    ),
                    (
                        "Bajo",
                        _require_float(
                            payload.reading_under_test_low_value,
                            "reading_under_test_low_value",
                        ),
                        _require_float(
                            payload.reference_reading_low_value,
                            "reference_reading_low_value",
                        ),
                    ),
                ]
                diffs: list[tuple[str, float, float, float]] = []
                for label, under_val, ref_val in readings:
                    reading_under_test_c = _temperature_to_celsius(
                        under_val, under_unit
                    )
                    reference_reading_c = _temperature_to_celsius(
                        ref_val, ref_unit
                    )
                    _validate_temperature_spec(temperature_spec, reading_under_test_c)
                    delta_c = abs(reading_under_test_c - reference_reading_c)
                    diffs.append((label, under_val, ref_val, delta_c))
                max_delta_c = 0.5 * 5.0 / 9.0
                comparison_ok = all(
                    delta_c <= max_delta_c for _, _, _, delta_c in diffs
                )
                if not comparison_ok:
                    comparison_message = (
                        "Difference between readings exceeds maximum 0.5 F."
                    )
            else:
                if use_unit_values:
                    reading_under_test_c = _temperature_to_celsius(
                        _require_float(
                            payload.reading_under_test_value,
                            "reading_under_test_value",
                        ),
                        _require_str(
                            payload.reading_under_test_unit,
                            "reading_under_test_unit",
                        ),
                    )
                    reference_reading_c = _temperature_to_celsius(
                        _require_float(
                            payload.reference_reading_value,
                            "reference_reading_value",
                        ),
                        _require_str(
                            payload.reference_reading_unit,
                            "reference_reading_unit",
                        ),
                    )
                else:
                    reading_under_test_c = _temperature_to_celsius(
                        _require_float(
                            payload.reading_under_test_f, "reading_under_test_f"
                        ),
                        "f",
                    )
                    reference_reading_c = _temperature_to_celsius(
                        _require_float(
                            payload.reference_reading_f, "reference_reading_f"
                        ),
                        "f",
                    )
                _validate_temperature_spec(temperature_spec, reading_under_test_c)
                delta_c = abs(reading_under_test_c - reference_reading_c)
                max_delta_c = 0.5 * 5.0 / 9.0
                comparison_ok = delta_c <= max_delta_c
                if not comparison_ok:
                    comparison_message = (
                        f"Difference between readings is {delta_c:.3f} C and exceeds maximum "
                        f"{max_delta_c:.3f} C."
                    )
        elif applies_tape_comparison_rule:
            if (
                not payload.reading_under_test_unit
                or not payload.reference_reading_unit
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Units are required for tape verification",
                )
            tape_under_unit = _require_str(
                payload.reading_under_test_unit, "reading_under_test_unit"
            )
            tape_ref_unit = _require_str(
                payload.reference_reading_unit, "reference_reading_unit"
            )
            tape_under_readings = _collect_two_or_three_readings(
                payload.reading_under_test_high_value,
                payload.reading_under_test_mid_value,
                payload.reading_under_test_low_value,
                "el equipo de trabajo",
            )
            tape_ref_readings = _collect_two_or_three_readings(
                payload.reference_reading_high_value,
                payload.reference_reading_mid_value,
                payload.reference_reading_low_value,
                "el equipo patron",
            )
            length_spec = _get_length_measure_spec(session, equipment_db_id)
            tape_under_mm: list[float] = []
            for reading in tape_under_readings:
                reading_mm = _length_to_millimeters(reading, tape_under_unit)
                _validate_length_spec(length_spec, reading_mm)
                tape_under_mm.append(reading_mm)
            tape_ref_mm = [
                _length_to_millimeters(reading, tape_ref_unit)
                for reading in tape_ref_readings
            ]
            tape_avg_under_mm = sum(tape_under_mm) / len(tape_under_mm)
            tape_avg_ref_mm = sum(tape_ref_mm) / len(tape_ref_mm)
            tape_diff_mm = tape_avg_ref_mm - tape_avg_under_mm
            comparison_ok = abs(tape_diff_mm) < 2.0
            if not comparison_ok:
                comparison_message = (
                    f"Diferencia promedio de cinta {tape_diff_mm:.3f} mm fuera del limite "
                    f"(< 2.000 mm)."
                )
        elif applies_balance_comparison_rule:
            if (
                payload.reading_under_test_value is None
                or not payload.reading_under_test_unit
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="reading_under_test_value and reading_under_test_unit are required for balance verification",
                )
            if (
                reference_equipment.nominal_mass_value is None
                or not reference_equipment.nominal_mass_unit
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference weight must have nominal mass defined",
                )
            try:
                balance_under_g = _weight_to_grams(
                    _require_float(
                        payload.reading_under_test_value,
                        "reading_under_test_value",
                    ),
                    _require_str(
                        payload.reading_under_test_unit,
                        "reading_under_test_unit",
                    ),
                )
                balance_ref_g = _weight_to_grams(
                    _require_float(
                        reference_equipment.nominal_mass_value,
                        "reference_equipment.nominal_mass_value",
                    ),
                    _require_str(
                        reference_equipment.nominal_mass_unit,
                        "reference_equipment.nominal_mass_unit",
                    ),
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            balance_diff_g = balance_ref_g - balance_under_g
            if equipment_type_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Equipment type is required for balance verification",
                )
            max_error_row = session.exec(
                select(EquipmentTypeMaxError).where(
                    EquipmentTypeMaxError.equipment_type_id == equipment_type_id,
                    EquipmentTypeMaxError.measure == EquipmentMeasureType.weight,
                )
            ).first()
            if max_error_row is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se encontro error maximo para la balanza.",
                )
            balance_max_error_g = max_error_row.max_error_value
            comparison_ok = abs(balance_diff_g) <= balance_max_error_g
            if not comparison_ok:
                comparison_message = (
                    "Diferencia entre pesa y balanza supera el error maximo permitido."
                )

    verification_ok = (
        all(is_ok is True for _, is_ok in evaluated_responses) and comparison_ok
    )
    notes = payload.notes
    if applies_comparison_rule or applies_kf_verification_rule:
        equipment_type_name = equipment_type.name if equipment_type else "Equipo"
        reference_equipment = cast(Equipment, reference_equipment)
        if applies_temperature_comparison_rule and is_monthly:
            under_unit = _require_str(
                payload.reading_under_test_unit, "reading_under_test_unit"
            )
            ref_unit = _require_str(
                payload.reference_reading_unit, "reference_reading_unit"
            )
            under_high = _require_float(
                payload.reading_under_test_high_value,
                "reading_under_test_high_value",
            )
            under_mid = _require_float(
                payload.reading_under_test_mid_value,
                "reading_under_test_mid_value",
            )
            under_low = _require_float(
                payload.reading_under_test_low_value,
                "reading_under_test_low_value",
            )
            ref_high = _require_float(
                payload.reference_reading_high_value,
                "reference_reading_high_value",
            )
            ref_mid = _require_float(
                payload.reference_reading_mid_value,
                "reference_reading_mid_value",
            )
            ref_low = _require_float(
                payload.reference_reading_low_value,
                "reference_reading_low_value",
            )
            delta_high = abs(
                _temperature_to_celsius(under_high, under_unit)
                - _temperature_to_celsius(ref_high, ref_unit)
            )
            delta_mid = abs(
                _temperature_to_celsius(under_mid, under_unit)
                - _temperature_to_celsius(ref_mid, ref_unit)
            )
            delta_low = abs(
                _temperature_to_celsius(under_low, under_unit)
                - _temperature_to_celsius(ref_low, ref_unit)
            )
            comparison_note = (
                f"Comparacion mensual {equipment_type_name} | "
                f"Patron ID: {payload.reference_equipment_id} | "
                f"Alto equipo: {under_high} {under_unit} | "
                f"Alto patron: {ref_high} {ref_unit} | "
                f"Dif Alto: {delta_high:.3f} C | "
                f"Medio equipo: {under_mid} {under_unit} | "
                f"Medio patron: {ref_mid} {ref_unit} | "
                f"Dif Medio: {delta_mid:.3f} C | "
                f"Bajo equipo: {under_low} {under_unit} | "
                f"Bajo patron: {ref_low} {ref_unit} | "
                f"Dif Bajo: {delta_low:.3f} C"
            )
        elif applies_temperature_comparison_rule:
            if use_unit_values:
                reading_under_test_label = f"{payload.reading_under_test_value} {payload.reading_under_test_unit}"
                reference_reading_label = f"{payload.reference_reading_value} {payload.reference_reading_unit}"
            else:
                reading_under_test_label = f"{payload.reading_under_test_f} F"
                reference_reading_label = f"{payload.reference_reading_f} F"
            comparison_note = (
                f"Comparacion {equipment_type_name} | "
                f"Patron ID: {payload.reference_equipment_id} | "
                f"Lectura equipo: {reading_under_test_label} | "
                f"Lectura patron: {reference_reading_label} | "
                f"Diferencia: {delta_c:.3f} C"
            )
        elif applies_balance_comparison_rule:
            ref_unit = reference_equipment.nominal_mass_unit or "g"
            under_unit = payload.reading_under_test_unit or "g"
            comparison_note = (
                f"Comparacion balanza {equipment_type_name} | "
                f"Patron ID: {payload.reference_equipment_id} | "
                f"Pesa: {reference_equipment.nominal_mass_value} {ref_unit} | "
                f"Lectura balanza: {payload.reading_under_test_value} {under_unit} | "
                f"Diferencia (Pesa-Balanza): {balance_diff_g:.6f} g | "
                f"Criterio: |Diferencia| <= {balance_max_error_g:.6g} g"
            )
        elif applies_kf_verification_rule:
            comparison_note = (
                "[[KF_DATA]] Verificacion Karl Fischer | "
                f"Balanza ID: {payload.reference_equipment_id} | "
                f"Peso1: {payload.kf_weight_1} g | "
                f"Volumen1: {payload.kf_volume_1} mL | "
                f"Factor1: {kf_factor_1:.6f} | "
                f"Peso2: {payload.kf_weight_2} g | "
                f"Volumen2: {payload.kf_volume_2} mL | "
                f"Factor2: {kf_factor_2:.6f} | "
                f"Factor promedio: {kf_factor_avg:.6f} | "
                f"Error relativo: {kf_error_rel:.3f}% | "
                "Criterio: Factores 4.5-5.5 y Error < 2%"
            )
        else:
            work_values = ", ".join(f"{value:g}" for value in tape_under_readings)
            ref_values = ", ".join(f"{value:g}" for value in tape_ref_readings)
            comparison_note = (
                f"Comparacion cinta {equipment_type_name} | "
                f"Patron ID: {payload.reference_equipment_id} | "
                f"Lecturas equipo: [{work_values}] {tape_under_unit} | "
                f"Promedio equipo: {tape_avg_under_mm:.3f} mm | "
                f"Lecturas patron: [{ref_values}] {tape_ref_unit} | "
                f"Promedio patron: {tape_avg_ref_mm:.3f} mm | "
                f"Diferencia (Patron-Equipo): {tape_diff_mm:.3f} mm | "
                "Criterio: |Diferencia| < 2.000 mm"
            )
        notes = (
            f"{payload.notes}\n{comparison_note}" if payload.notes else comparison_note
        )

    verification.verification_type_id = verification_type_id
    verification.verified_at = verified_at
    verification.notes = notes
    verification.is_ok = verification_ok
    session.add(verification)
    verification_db_id = _require_id(verification.id, "Verification")
    session.exec(
        delete(EquipmentVerificationResponse).where(
            EquipmentVerificationResponse.verification_id == verification_db_id  # type: ignore[arg-type]
        )
    )
    for response, is_ok in evaluated_responses:
        session.add(
            EquipmentVerificationResponse(
                verification_id=verification_db_id,
                verification_item_id=response.verification_item_id,
                response_type=response.response_type,
                value_bool=response.value_bool,
                value_text=response.value_text,
                value_number=response.value_number,
                is_ok=is_ok,
            )
        )
    session.commit()
    session.refresh(verification)

    responses = session.exec(
        select(EquipmentVerificationResponse).where(
            EquipmentVerificationResponse.verification_id == verification_db_id
        )
    ).all()
    message: str | None = None
    if verification_ok is False:
        equipment.status = EquipmentStatus.needs_review
        session.add(equipment)
        session.commit()
        message = (
            comparison_message
            or "Verification failed. Equipment status set to needs_review."
        )
    if verification_ok is True:
        equipment.status = EquipmentStatus.in_use
        session.add(equipment)
        session.commit()
    verification_read = EquipmentVerificationRead.model_validate(
        verification, from_attributes=True
    )
    verification_read.responses = [
        EquipmentVerificationResponseRead.model_validate(r, from_attributes=True)
        for r in responses
    ]
    monthly = _parse_monthly_readings_from_notes(verification_read.notes)
    if monthly:
        for key, value in monthly.items():
            setattr(verification_read, key, value)
    verification_read.message = message or comparison_message
    return verification_read


@router.get(
    "/equipment/{equipment_id}",
    response_model=EquipmentVerificationListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment_verifications(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentVerificationListResponse:
    """
    Lista verificaciones de un equipo.

    Permisos: `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: equipo no encontrado.
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

    verifications = session.exec(
        select(EquipmentVerification).where(
            EquipmentVerification.equipment_id == equipment.id
        )
    ).all()
    if not verifications:
        return EquipmentVerificationListResponse(message="No records found")
    items = []
    for verification in verifications:
        responses = session.exec(
            select(EquipmentVerificationResponse).where(
                EquipmentVerificationResponse.verification_id == verification.id
            )
        ).all()
        items.append(
            EquipmentVerificationRead(
                **verification.model_dump(),
                responses=[
                    EquipmentVerificationResponseRead.model_validate(
                        r, from_attributes=True
                    )
                    for r in responses
                ],
            )
        )
    return EquipmentVerificationListResponse(items=items)


@router.get(
    "/{verification_id}",
    response_model=EquipmentVerificationRead,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def get_verification(
    verification_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentVerificationRead:
    """
    Obtiene una verificación por ID.

    Permisos: `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    """
    verification = session.get(EquipmentVerification, verification_id)
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found",
        )
    responses = session.exec(
        select(EquipmentVerificationResponse).where(
            EquipmentVerificationResponse.verification_id == verification.id
        )
    ).all()
    return EquipmentVerificationRead(
        **verification.model_dump(),
        responses=[
            EquipmentVerificationResponseRead.model_validate(r, from_attributes=True)
            for r in responses
        ],
    )
