import math
import re
from datetime import UTC, datetime, timedelta
from typing import assert_never, cast

from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlmodel import Session, select

from app.models.enums import (
    EquipmentMeasureType,
    EquipmentRole,
    EquipmentStatus,
    InspectionResponseType,
)
from app.models.equipment import Equipment
from app.models.equipment_calibration import EquipmentCalibration
from app.models.equipment_inspection import EquipmentInspection
from app.models.equipment_measure_spec import EquipmentMeasureSpec
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_measure import EquipmentTypeMeasure
from app.models.equipment_type_verification_item import EquipmentTypeVerificationItem
from app.models.equipment_verification import (
    EquipmentVerification,
    EquipmentVerificationCreate,
    EquipmentVerificationRead,
    EquipmentVerificationResponse,
    EquipmentVerificationResponseCreate,
    EquipmentVerificationResponseRead,
    EquipmentVerificationUpdate,
)
from app.utils.equipment_status_history import record_equipment_status_change
from app.utils.measurements.length import Length
from app.utils.measurements.temperature import Temperature
from app.utils.measurements.weight import Weight


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


def _get_api_measure_spec(
    session: Session, equipment_id: int
) -> EquipmentMeasureSpec | None:
    return session.exec(
        select(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equipment_id,
            EquipmentMeasureSpec.measure == EquipmentMeasureType.api,
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


def _resolution_decimals(
    resolution: float | None, *, fallback: int = 3
) -> int:
    if resolution is None or resolution <= 0:
        return fallback
    normalized = f"{resolution:.10f}".rstrip("0").rstrip(".")
    if "." not in normalized:
        return 0
    return min(6, len(normalized.split(".")[1]))


def _format_with_resolution(
    value: float, resolution: float | None, *, fallback_decimals: int = 3
) -> str:
    decimals = _resolution_decimals(resolution, fallback=fallback_decimals)
    return f"{value:.{decimals}f}"


def _validate_api_spec(
    api_spec: EquipmentMeasureSpec | None,
    reading_api: float,
    reading_label: str,
) -> None:
    if not api_spec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No existe especificaciÃ³n API configurada para {reading_label}."
            ),
        )
    if api_spec.min_value is not None and reading_api < api_spec.min_value:
        min_label = _format_with_resolution(api_spec.min_value, api_spec.resolution)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La {reading_label} estÃ¡ por debajo del mÃ­nimo permitido "
                f"({min_label} API)"
            ),
        )
    if api_spec.max_value is not None and reading_api > api_spec.max_value:
        max_label = _format_with_resolution(api_spec.max_value, api_spec.resolution)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La {reading_label} estÃ¡ por encima del mÃ¡ximo permitido "
                f"({max_label} API)"
            ),
        )
    if (
        api_spec.resolution is not None
        and api_spec.resolution > 0
        and not _matches_resolution(reading_api, api_spec.resolution)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La {reading_label} no coincide con la resoluciÃ³n del equipo "
                f"({api_spec.resolution:.6g} API)"
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


def _evaluate_kf_verification(
    session: Session,
    *,
    reference_equipment: Equipment,
    payload: EquipmentVerificationCreate | EquipmentVerificationUpdate,
) -> tuple[float, float, float, float, bool, str | None]:
    kf_reference_type = session.get(EquipmentType, reference_equipment.equipment_type_id)
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
    comparison_message = None
    if not comparison_ok:
        comparison_message = "Factor fuera de 4.5-5.5 o error relativo >= 2%."

    return (
        kf_factor_1,
        kf_factor_2,
        kf_factor_avg,
        kf_error_rel,
        comparison_ok,
        comparison_message,
    )


def _apply_verification_equipment_status(
    session: Session,
    *,
    equipment: Equipment,
    equipment_id: int,
    changed_by_user_id: int,
    verification_ok: bool,
    comparison_message: str | None,
) -> str | None:
    if verification_ok:
        if equipment.status != EquipmentStatus.in_use:
            record_equipment_status_change(
                session,
                equipment_id=equipment_id,
                new_status=EquipmentStatus.in_use,
                changed_by_user_id=changed_by_user_id,
            )
            equipment.status = EquipmentStatus.in_use
            session.add(equipment)
        return None

    if equipment.status != EquipmentStatus.needs_review:
        record_equipment_status_change(
            session,
            equipment_id=equipment_id,
            new_status=EquipmentStatus.needs_review,
            changed_by_user_id=changed_by_user_id,
        )
        equipment.status = EquipmentStatus.needs_review
        session.add(equipment)

    return (
        comparison_message
        or "Verification failed. Equipment status set to needs_review."
    )


def _build_verification_read(
    session: Session,
    verification: EquipmentVerification,
    *,
    message: str | None = None,
) -> EquipmentVerificationRead:
    verification_db_id = _require_id(verification.id, "Verification")
    responses = session.exec(
        select(EquipmentVerificationResponse).where(
            EquipmentVerificationResponse.verification_id == verification_db_id
        )
    ).all()
    verification_read = EquipmentVerificationRead.model_validate(
        verification,
        from_attributes=True,
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


