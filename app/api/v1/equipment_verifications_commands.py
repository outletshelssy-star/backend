from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, delete, select

from app.api.v1.equipment_verifications_shared import (
    _apply_verification_equipment_status,
    _as_utc,
    _build_verification_read,
    _collect_two_or_three_readings,
    _evaluate_kf_verification,
    _evaluate_response,
    _get_api_measure_spec,
    _get_length_measure_spec,
    _get_temperature_measure_spec,
    _has_approved_daily_inspection,
    _has_length_measure,
    _has_temperature_measure,
    _is_hydrometer_type_name,
    _is_kf_type_name,
    _is_tape_type_name,
    _length_to_millimeters,
    _require_float,
    _require_id,
    _require_str,
    _require_valid_calibration,
    _requires_balance_comparison,
    _requires_tape_comparison,
    _requires_temperature_comparison,
    _temperature_to_celsius,
    _validate_api_spec,
    _validate_length_spec,
    _validate_response,
    _validate_temperature_spec,
    _weight_to_grams,
)
from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.enums import EquipmentMeasureType, EquipmentRole, EquipmentStatus, UserType
from app.models.equipment import Equipment
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_max_error import EquipmentTypeMaxError
from app.models.equipment_type_verification import EquipmentTypeVerification
from app.models.equipment_type_verification_item import EquipmentTypeVerificationItem
from app.models.equipment_verification import (
    EquipmentVerification,
    EquipmentVerificationCreate,
    EquipmentVerificationRead,
    EquipmentVerificationResponse,
    EquipmentVerificationResponseCreate,
    EquipmentVerificationUpdate,
)
from app.models.user import User
from app.models.user_terminal import UserTerminal
from app.utils.emp_weights import get_emp
from app.utils.hydrometer import api_60f_crude

router = APIRouter()
@router.post(
    "/equipment/{equipment_id}",
    response_model=EquipmentVerificationRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_400_BAD_REQUEST: {"description": "Solicitud invÃ¡lida"},
    },
)
def create_equipment_verification(
    equipment_id: int,
    payload: EquipmentVerificationCreate,
    replace_existing: bool = Query(
        False,
        alias="replace_existing",
        description="Si es `true`, reemplaza la verificaciÃ³n abierta existente.",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> EquipmentVerificationRead:
    """
    Crea una verificaciÃ³n para un equipo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    ParÃ¡metros:
    - `replace_existing`: si es `true`, reemplaza la verificaciÃ³n abierta del dÃ­a.
    Respuestas:
    - 400: solicitud invÃ¡lida.
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
    reference_equipment: Equipment | None = None
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
                work_reading_api = _require_float(
                    payload.reading_under_test_value, "reading_under_test_value"
                )
                ref_reading_api = _require_float(
                    payload.reference_reading_value, "reference_reading_value"
                )
                _validate_api_spec(
                    _get_api_measure_spec(session, equipment_db_id),
                    work_reading_api,
                    "lectura del hidrÃ³metro de trabajo",
                )
                _validate_api_spec(
                    _get_api_measure_spec(session, reference_equipment_id),
                    ref_reading_api,
                    "lectura del hidrÃ³metro patrÃ³n",
                )
                work_api60 = api_60f_crude(
                    _require_float(
                        payload.reading_under_test_f, "reading_under_test_f"
                    ),
                    work_reading_api,
                )
                ref_api60 = api_60f_crude(
                    _require_float(
                        payload.reference_reading_f, "reference_reading_f"
                    ),
                    ref_reading_api,
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
        if reference_equipment is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reference_equipment_id is required for Karl Fischer verification",
            )
        (
            kf_factor_1,
            kf_factor_2,
            kf_factor_avg,
            kf_error_rel,
            comparison_ok,
            comparison_message,
        ) = _evaluate_kf_verification(
            session,
            reference_equipment=reference_equipment,
            payload=payload,
        )
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
                detail="Ya se realizÃ³ una verificaciÃ³n hoy. Â¿Deseas reemplazarla?",
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
        elif applies_hydrometer_comparison_rule:
            comparison_note = (
                f"API60F equipo: {work_api60:.1f} API | "
                f"API60F patron: {ref_api60:.1f} API | "
                f"Diferencia API60F: {diff_api:.2f} API | "
                "Criterio: |Diferencia| <= 0.5 API"
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
    session.flush()
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
    message = _apply_verification_equipment_status(
        session,
        equipment=equipment,
        equipment_id=equipment_db_id,
        changed_by_user_id=current_user.id,
        verification_ok=verification_ok,
        comparison_message=comparison_message,
    )
    session.commit()
    session.refresh(verification)
    return _build_verification_read(
        session,
        verification,
        message=message,
    )


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
    Actualiza una verificaciÃ³n existente por ID.

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
            detail="Ya existe una verificaciÃ³n para esta fecha.",
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
    reference_equipment: Equipment | None = None
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
                work_reading_api = _require_float(
                    payload.reading_under_test_value, "reading_under_test_value"
                )
                ref_reading_api = _require_float(
                    payload.reference_reading_value, "reference_reading_value"
                )
                _validate_api_spec(
                    _get_api_measure_spec(session, equipment_db_id),
                    work_reading_api,
                    "lectura del hidrÃ³metro de trabajo",
                )
                _validate_api_spec(
                    _get_api_measure_spec(session, reference_equipment_id),
                    ref_reading_api,
                    "lectura del hidrÃ³metro patrÃ³n",
                )
                work_api60 = api_60f_crude(
                    _require_float(
                        payload.reading_under_test_f, "reading_under_test_f"
                    ),
                    work_reading_api,
                )
                ref_api60 = api_60f_crude(
                    _require_float(
                        payload.reference_reading_f, "reference_reading_f"
                    ),
                    ref_reading_api,
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
    if applies_kf_verification_rule:
        if reference_equipment is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reference_equipment_id is required for Karl Fischer verification",
            )
        (
            kf_factor_1,
            kf_factor_2,
            kf_factor_avg,
            kf_error_rel,
            comparison_ok,
            comparison_message,
        ) = _evaluate_kf_verification(
            session,
            reference_equipment=reference_equipment,
            payload=payload,
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
        elif applies_hydrometer_comparison_rule:
            comparison_note = (
                f"API60F equipo: {work_api60:.1f} API | "
                f"API60F patron: {ref_api60:.1f} API | "
                f"Diferencia API60F: {diff_api:.2f} API | "
                "Criterio: |Diferencia| <= 0.5 API"
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
    message = _apply_verification_equipment_status(
        session,
        equipment=equipment,
        equipment_id=equipment_db_id,
        changed_by_user_id=current_user.id,
        verification_ok=verification_ok,
        comparison_message=comparison_message,
    )
    session.commit()
    session.refresh(verification)
    return _build_verification_read(
        session,
        verification,
        message=message or comparison_message,
    )


@router.delete(
    "/{verification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def delete_equipment_verification(
    verification_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> None:
    """
    Elimina una verificación por ID (incluyendo sus respuestas).

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
    equipment = session.get(Equipment, verification.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    terminal_ids = {
        row.terminal_id
        for row in session.exec(
            select(UserTerminal).where(UserTerminal.user_id == current_user.id)
        ).all()
    }
    if (
        current_user.user_type not in {UserType.superadmin, UserType.admin}
        or (
            current_user.user_type == UserType.admin
            and equipment.terminal_id is not None
            and equipment.terminal_id not in terminal_ids
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este equipo",
        )
    session.exec(
        delete(EquipmentVerificationResponse).where(
            EquipmentVerificationResponse.verification_id == verification_id  # type: ignore[arg-type]
        )
    )
    session.delete(verification)
    session.commit()

