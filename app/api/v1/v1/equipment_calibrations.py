from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, delete, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.company import Company
from app.models.enums import EquipmentMeasureType, UserType
from app.models.equipment import Equipment
from app.models.equipment_calibration import (
    EquipmentCalibration,
    EquipmentCalibrationCreate,
    EquipmentCalibrationListResponse,
    EquipmentCalibrationRead,
    EquipmentCalibrationResult,
    EquipmentCalibrationResultCreate,
    EquipmentCalibrationResultRead,
    EquipmentCalibrationUpdate,
)
from app.models.equipment_type_max_error import EquipmentTypeMaxError
from app.models.equipment_type_measure import EquipmentTypeMeasure
from app.models.user import User
from app.models.user_terminal import UserTerminal
from app.services.supabase_storage import upload_calibration_certificate
from app.utils.measurements.length import Length
from app.utils.measurements.temperature import Temperature
from app.utils.measurements.weight import Weight
from app.utils.emp_weights import get_emp

router = APIRouter(
    prefix="/equipment-calibrations",
    tags=["Equipment Calibrations"],
)


def _as_utc(dt_value: datetime) -> datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=UTC)
    return dt_value.astimezone(UTC)


def _validate_company(
    session: Session,
    calibration_company_id: int | None,
    calibration_company_name: str | None,
) -> tuple[int | None, str | None]:
    cleaned_name = (
        calibration_company_name.strip()
        if isinstance(calibration_company_name, str)
        else None
    )
    if not calibration_company_id and not cleaned_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="calibration_company_id or calibration_company_name is required",
        )
    if calibration_company_id:
        company = session.get(Company, calibration_company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calibration company not found",
            )
    return calibration_company_id, cleaned_name


def _check_terminal_access(
    session: Session,
    user: User,
    equipment: Equipment,
) -> None:
    if user.user_type == UserType.superadmin:
        return
    allowed_terminal_ids = session.exec(
        select(UserTerminal.terminal_id).where(UserTerminal.user_id == user.id)
    ).all()
    if allowed_terminal_ids and equipment.terminal_id not in set(allowed_terminal_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this terminal",
        )


def _infer_measure_from_unit(unit: str | None) -> EquipmentMeasureType | None:
    if not unit:
        return None
    unit_key = unit.strip().lower()
    if unit_key in {"c", "f", "k", "r", "celsius", "fahrenheit", "kelvin", "rankine"}:
        return EquipmentMeasureType.temperature
    if unit_key in {"mm", "cm", "m", "in", "ft", "millimeter", "millimeters", "centimeter", "centimeters", "meter", "meters", "inch", "inches", "foot", "feet"}:
        return EquipmentMeasureType.length
    if unit_key in {"g", "kg", "lb", "lbs", "oz", "mg", "gram", "grams", "kilogram", "kilograms", "pound", "pounds", "ounce", "ounces", "milligram", "milligrams"}:
        return EquipmentMeasureType.weight
    if unit_key in {"api"}:
        return EquipmentMeasureType.api
    if unit_key in {"%p/v", "%pv", "p/v", "%w/v"}:
        return EquipmentMeasureType.percent_pv
    return None


def _normalize_uncertainty_value(
    value: float,
    measure: EquipmentMeasureType,
    unit: str | None,
) -> float:
    if measure == EquipmentMeasureType.temperature:
        unit_key = (unit or "c").strip().lower()
        if unit_key in {"c", "celsius"}:
            return value
        if unit_key in {"f", "fahrenheit"}:
            return value * 5.0 / 9.0
        if unit_key in {"k", "kelvin"}:
            return value
        if unit_key in {"r", "rankine"}:
            return value * 5.0 / 9.0
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported temperature unit for uncertainty",
        )
    if measure == EquipmentMeasureType.length:
        unit_key = (unit or "mm").strip().lower()
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported length unit for uncertainty",
        )
    if measure == EquipmentMeasureType.weight:
        unit_key = (unit or "g").strip().lower()
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
            detail="Unsupported weight unit for uncertainty",
        )
    if measure == EquipmentMeasureType.api:
        unit_key = (unit or "api").strip().lower()
        if unit_key in {"api"}:
            return value
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported API unit for uncertainty",
        )
    if measure == EquipmentMeasureType.percent_pv:
        unit_key = (unit or "%p/v").strip().lower().replace(" ", "")
        if unit_key in {"%p/v", "%pv", "p/v", "%w/v", "ml", "l"}:
            return value
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported percent p/v unit for uncertainty",
        )
    return value


def _validate_uncertainty_max_error(
    session: Session,
    equipment: Equipment,
    results: list[EquipmentCalibrationResultCreate],
) -> None:
    if not results:
        return
    emp_value = equipment.emp_value
    if emp_value is not None and emp_value <= 0:
        emp_value = None
    if (
        emp_value is None
        and equipment.weight_class
        and equipment.nominal_mass_value is not None
        and equipment.nominal_mass_unit
    ):
        try:
            emp_value = get_emp(
                equipment.weight_class,
                equipment.nominal_mass_value,
                equipment.nominal_mass_unit,
            )
        except ValueError:
            emp_value = equipment.emp_value
    is_weight_equipment = (
        emp_value is not None
        and equipment.weight_class
        and equipment.nominal_mass_value is not None
    )
    measures = session.exec(
        select(EquipmentTypeMeasure.measure).where(
            EquipmentTypeMeasure.equipment_type_id == equipment.equipment_type_id
        )
    ).all()
    max_errors_rows = session.exec(
        select(EquipmentTypeMaxError).where(
            EquipmentTypeMaxError.equipment_type_id == equipment.equipment_type_id
        )
    ).all()
    if not max_errors_rows and emp_value is None:
        return
    max_error_by_measure = {row.measure: row.max_error_value for row in max_errors_rows}
    for row in results:
        uncertainty_value = (
            row.uncertainty_value
            if row.uncertainty_value is not None
            else row.error_value
        )
        if uncertainty_value is None:
            continue
        if is_weight_equipment:
            measure = EquipmentMeasureType.weight
            max_error = emp_value
        else:
            measure: EquipmentMeasureType | None = None
            if len(measures) == 1:
                measure = measures[0]
            else:
                measure = _infer_measure_from_unit(row.unit)
            if measure is None and emp_value is not None:
                measure = EquipmentMeasureType.weight
            if measure is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pudo determinar la medida para validar la incertidumbre.",
                )
            if measure == EquipmentMeasureType.weight and emp_value is not None:
                max_error = emp_value
            else:
                max_error = max_error_by_measure.get(measure)
        if max_error is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontro error maximo para el tipo de equipo.",
            )
        normalized = _normalize_uncertainty_value(uncertainty_value, measure, row.unit)
        if normalized > max_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "La incertidumbre supera el error maximo permitido "
                    f"({max_error:.6g})."
                ),
            )


def _read_with_results(
    session: Session,
    calibration: EquipmentCalibration,
) -> EquipmentCalibrationRead:
    rows = session.exec(
        select(EquipmentCalibrationResult).where(
            EquipmentCalibrationResult.calibration_id == calibration.id
        )
    ).all()
    return EquipmentCalibrationRead(
        **calibration.model_dump(),
        results=[
            EquipmentCalibrationResultRead.model_validate(r, from_attributes=True)
            for r in rows
        ],
    )


def _replace_results(
    session: Session,
    calibration_id: int,
    rows: list[EquipmentCalibrationResultCreate],
) -> None:
    session.exec(
        delete(EquipmentCalibrationResult).where(
            EquipmentCalibrationResult.calibration_id == calibration_id
        )
    )
    for row in rows:
        session.add(
            EquipmentCalibrationResult(
                calibration_id=calibration_id,
                point_label=row.point_label,
                reference_value=row.reference_value,
                measured_value=row.measured_value,
                unit=row.unit.strip() if isinstance(row.unit, str) else None,
                error_value=row.error_value,
                tolerance_value=row.tolerance_value,
                volume_value=row.volume_value,
                systematic_error=row.systematic_error,
                systematic_emp=row.systematic_emp,
                random_error=row.random_error,
                random_emp=row.random_emp,
                uncertainty_value=row.uncertainty_value,
                k_value=row.k_value,
                is_ok=row.is_ok,
                notes=row.notes,
            )
        )


@router.post(
    "/equipment/{equipment_id}",
    response_model=EquipmentCalibrationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_equipment_calibration(
    equipment_id: int,
    payload: EquipmentCalibrationCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentCalibrationRead:
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
    _check_terminal_access(session, current_user, equipment)

    calibration_company_id, calibration_company_name = _validate_company(
        session,
        payload.calibration_company_id,
        payload.calibration_company_name,
    )
    if not payload.certificate_number or not payload.certificate_number.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="certificate_number is required",
        )
    _validate_uncertainty_max_error(session, equipment, payload.results)
    calibrated_at = _as_utc(payload.calibrated_at) if payload.calibrated_at else datetime.now(UTC)

    calibration = EquipmentCalibration(
        equipment_id=equipment.id,
        calibrated_at=calibrated_at,
        created_by_user_id=current_user.id,
        calibration_company_id=calibration_company_id,
        calibration_company_name=calibration_company_name,
        certificate_number=payload.certificate_number.strip(),
        notes=payload.notes,
    )
    session.add(calibration)
    session.commit()
    session.refresh(calibration)

    _replace_results(session, calibration.id, payload.results)
    session.commit()
    session.refresh(calibration)
    return _read_with_results(session, calibration)


@router.get(
    "/equipment/{equipment_id}",
    response_model=EquipmentCalibrationListResponse,
    status_code=status.HTTP_200_OK,
)
def list_equipment_calibrations(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> Any:
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    _check_terminal_access(session, current_user, equipment)

    calibrations = session.exec(
        select(EquipmentCalibration).where(
            EquipmentCalibration.equipment_id == equipment_id
        )
    ).all()
    if not calibrations:
        return EquipmentCalibrationListResponse(message="No records found")

    return EquipmentCalibrationListResponse(
        items=[_read_with_results(session, item) for item in calibrations]
    )


@router.get(
    "/{calibration_id}",
    response_model=EquipmentCalibrationRead,
    status_code=status.HTTP_200_OK,
)
def get_equipment_calibration(
    calibration_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentCalibrationRead:
    calibration = session.get(EquipmentCalibration, calibration_id)
    if not calibration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calibration not found",
        )
    equipment = session.get(Equipment, calibration.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    _check_terminal_access(session, current_user, equipment)
    return _read_with_results(session, calibration)


@router.patch(
    "/{calibration_id}",
    response_model=EquipmentCalibrationRead,
    status_code=status.HTTP_200_OK,
)
def update_equipment_calibration(
    calibration_id: int,
    payload: EquipmentCalibrationUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentCalibrationRead:
    calibration = session.get(EquipmentCalibration, calibration_id)
    if not calibration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calibration not found",
        )
    equipment = session.get(Equipment, calibration.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    _check_terminal_access(session, current_user, equipment)

    if payload.calibrated_at is not None:
        calibration.calibrated_at = _as_utc(payload.calibrated_at)
    if (
        payload.calibration_company_id is not None
        or payload.calibration_company_name is not None
    ):
        company_id, company_name = _validate_company(
            session,
            payload.calibration_company_id,
            payload.calibration_company_name,
        )
        calibration.calibration_company_id = company_id
        calibration.calibration_company_name = company_name
    if payload.certificate_number is not None:
        calibration.certificate_number = payload.certificate_number
    if payload.notes is not None:
        calibration.notes = payload.notes
    if payload.certificate_pdf_url is not None:
        calibration.certificate_pdf_url = payload.certificate_pdf_url
    if payload.certificate_number is not None:
        if not payload.certificate_number.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="certificate_number is required",
            )
        calibration.certificate_number = payload.certificate_number.strip()

    session.add(calibration)
    if payload.results is not None:
        _validate_uncertainty_max_error(session, equipment, payload.results)
        _replace_results(session, calibration.id, payload.results)
    session.commit()
    session.refresh(calibration)
    return _read_with_results(session, calibration)


@router.post(
    "/{calibration_id}/certificate",
    response_model=EquipmentCalibrationRead,
    status_code=status.HTTP_200_OK,
)
def upload_equipment_calibration_certificate(
    calibration_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentCalibrationRead:
    calibration = session.get(EquipmentCalibration, calibration_id)
    if not calibration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calibration not found",
        )
    equipment = session.get(Equipment, calibration.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )
    _check_terminal_access(session, current_user, equipment)

    certificate_url = upload_calibration_certificate(file, calibration_id)
    calibration.certificate_pdf_url = certificate_url
    session.add(calibration)
    session.commit()
    session.refresh(calibration)
    return _read_with_results(session, calibration)
