from typing import Any

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, delete, select

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
from app.models.equipment_measure_spec import (
    EquipmentMeasureSpec,
    EquipmentMeasureSpecCreate,
    EquipmentMeasureSpecRead,
)
from app.models.equipment_inspection import (
    EquipmentInspection,
    EquipmentInspectionRead,
    EquipmentInspectionResponse,
    EquipmentInspectionResponseRead,
)
from app.models.equipment_verification import (
    EquipmentVerification,
    EquipmentVerificationRead,
    EquipmentVerificationResponse,
    EquipmentVerificationResponseRead,
)
from app.models.equipment_calibration import (
    EquipmentCalibration,
    EquipmentCalibrationRead,
    EquipmentCalibrationResult,
    EquipmentCalibrationResultRead,
)
from app.api.v1.equipment_verifications import _parse_monthly_readings_from_notes
from app.models.equipment_reading import EquipmentReading
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_history import (
    EquipmentTypeHistory,
    EquipmentTypeHistoryListResponse,
    EquipmentTypeHistoryRead,
)
from app.models.user_terminal import UserTerminal
from app.models.user import User
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





def _replace_component_serials(
    session: Session,
    equipment_id: int,
    component_serials: list[EquipmentComponentSerialCreate],
) -> None:
    session.exec(
        delete(EquipmentComponentSerial).where(
            EquipmentComponentSerial.equipment_id == equipment_id
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
    return [
        EquipmentComponentSerialRead(**row.model_dump())
        for row in rows
    ]
@router.post(
    "/",
    response_model=EquipmentReadWithIncludes,
    status_code=status.HTTP_201_CREATED,
)
def create_equipment(
    equipment_in: EquipmentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentReadWithIncludes:
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
    )

    session.add(equipment)
    session.commit()
    session.refresh(equipment)

    session.add(
        EquipmentTypeHistory(
            equipment_id=equipment.id,
            equipment_type_id=equipment.equipment_type_id,
            changed_by_user_id=current_user.id,
        )
    )
    session.commit()

    _replace_component_serials(
        session,
        equipment.id,
        equipment_in.component_serials,
    )

    for spec in equipment_in.measure_specs:
        if spec.measure not in {
            EquipmentMeasureType.temperature,
            EquipmentMeasureType.weight,
            EquipmentMeasureType.length,
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
                equipment_id=equipment.id,
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
            EquipmentMeasureSpec.equipment_id == equipment.id
        )
    ).all()
    response.measure_specs = [
        EquipmentMeasureSpecRead(**s.model_dump())
        for s in measure_specs
    ]
    response.component_serials = _get_component_serials(session, equipment.id)
    return response


@router.get(
    "/",
    response_model=EquipmentListResponse,
    status_code=status.HTTP_200_OK,
)
def list_equipment(
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
    include: str | None = Query(default=None),
) -> Any:
    statement = select(Equipment)
    allowed_terminal_ids = _get_allowed_terminal_ids(session, current_user)
    if allowed_terminal_ids:
        statement = statement.where(Equipment.terminal_id.in_(allowed_terminal_ids))
    equipment_items = session.exec(statement).all()
    if not equipment_items:
        return EquipmentListResponse(message="No records found")
    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }
    items: list[EquipmentReadWithIncludes] = []
    for equipment in equipment_items:
        measure_specs = session.exec(
            select(EquipmentMeasureSpec).where(
                EquipmentMeasureSpec.equipment_id == equipment.id
            )
        ).all()
        item = EquipmentReadWithIncludes.model_validate(
            equipment,
            from_attributes=True,
        )
        item.measure_specs = [
            EquipmentMeasureSpecRead(**s.model_dump())
            for s in measure_specs
        ]
        item.component_serials = _get_component_serials(session, equipment.id)
        if include_set:
            if "equipment_type" in include_set:
                item.equipment_type = session.get(
                    EquipmentType, equipment.equipment_type_id
                )
            if "owner_company" in include_set:
                item.owner_company = session.get(
                    Company, equipment.owner_company_id
                )
            if "terminal" in include_set:
                item.terminal = session.get(
                    CompanyTerminal, equipment.terminal_id
                )
            if "creator" in include_set:
                item.creator = session.get(
                    User, equipment.created_by_user_id
                )
            if "inspections" in include_set:
                inspections = session.exec(
                    select(EquipmentInspection).where(
                        EquipmentInspection.equipment_id == equipment.id
                    )
                ).all()
                inspection_items: list[EquipmentInspectionRead] = []
                for inspection in inspections:
                    responses = session.exec(
                        select(EquipmentInspectionResponse).where(
                            EquipmentInspectionResponse.inspection_id
                            == inspection.id
                        )
                    ).all()
                    inspection_items.append(
                        EquipmentInspectionRead(
                            **inspection.model_dump(),
                            responses=[
                                EquipmentInspectionResponseRead(**r.model_dump())
                                for r in responses
                            ],
                        )
                    )
                item.inspections = inspection_items
            if "verifications" in include_set:
                verifications = session.exec(
                    select(EquipmentVerification).where(
                        EquipmentVerification.equipment_id == equipment.id
                    )
                ).all()
                verification_items: list[EquipmentVerificationRead] = []
                for verification in verifications:
                    responses = session.exec(
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
                                for r in responses
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
                        EquipmentCalibration.equipment_id == equipment.id
                    )
                ).all()
                calibration_items: list[EquipmentCalibrationRead] = []
                for calibration in calibrations:
                    results = session.exec(
                        select(EquipmentCalibrationResult).where(
                            EquipmentCalibrationResult.calibration_id
                            == calibration.id
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
)
def get_equipment(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
    include: str | None = Query(default=None),
) -> EquipmentReadWithIncludes:
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
    response = EquipmentReadWithIncludes.model_validate(
        equipment,
        from_attributes=True,
    )
    measure_specs = session.exec(
        select(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equipment.id
        )
    ).all()
    response.measure_specs = [
        EquipmentMeasureSpecRead(**s.model_dump())
        for s in measure_specs
    ]
    response.component_serials = _get_component_serials(session, equipment.id)
    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }
    if include_set:
        if "equipment_type" in include_set:
            response.equipment_type = session.get(
                EquipmentType, equipment.equipment_type_id
            )
        if "owner_company" in include_set:
            response.owner_company = session.get(
                Company, equipment.owner_company_id
            )
        if "terminal" in include_set:
            response.terminal = session.get(
                CompanyTerminal, equipment.terminal_id
            )
        if "creator" in include_set:
            response.creator = session.get(
                User, equipment.created_by_user_id
            )
        if "inspections" in include_set:
            inspections = session.exec(
                select(EquipmentInspection).where(
                    EquipmentInspection.equipment_id == equipment.id
                )
            ).all()
            inspection_items: list[EquipmentInspectionRead] = []
            for inspection in inspections:
                responses = session.exec(
                    select(EquipmentInspectionResponse).where(
                        EquipmentInspectionResponse.inspection_id
                        == inspection.id
                    )
                ).all()
                inspection_items.append(
                    EquipmentInspectionRead(
                        **inspection.model_dump(),
                        responses=[
                            EquipmentInspectionResponseRead(**r.model_dump())
                            for r in responses
                        ],
                    )
                )
            response.inspections = inspection_items
        if "verifications" in include_set:
            verifications = session.exec(
                select(EquipmentVerification).where(
                    EquipmentVerification.equipment_id == equipment.id
                )
            ).all()
            verification_items: list[EquipmentVerificationRead] = []
            for verification in verifications:
                responses = session.exec(
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
                            for r in responses
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
                    EquipmentCalibration.equipment_id == equipment.id
                )
            ).all()
            calibration_items: list[EquipmentCalibrationRead] = []
            for calibration in calibrations:
                results = session.exec(
                    select(EquipmentCalibrationResult).where(
                        EquipmentCalibrationResult.calibration_id
                        == calibration.id
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
)
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentReadWithIncludes:
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

    update_data = payload.model_dump(exclude_unset=True)
    specs = update_data.pop("measure_specs", None)
    component_serials = update_data.pop("component_serials", None)

    if "equipment_type_id" in update_data:
        equipment_type_id = update_data["equipment_type_id"]
        if equipment_type_id is not None:
            equipment_type = session.get(EquipmentType, equipment_type_id)
            if not equipment_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Equipment type not found",
                )

            current_history = session.exec(
                select(EquipmentTypeHistory).where(
                    EquipmentTypeHistory.equipment_id == equipment.id,
                    EquipmentTypeHistory.ended_at.is_(None),
                )
            ).first()
            if current_history:
                current_history.ended_at = datetime.now(UTC)
                session.add(current_history)

            session.add(
                EquipmentTypeHistory(
                    equipment_id=equipment.id,
                    equipment_type_id=equipment_type_id,
                    changed_by_user_id=current_user.id,
                )
            )

    if "owner_company_id" in update_data:
        owner_company_id = update_data["owner_company_id"]
        if owner_company_id is not None and not session.get(
            Company, owner_company_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Owner company not found",
            )

    if "terminal_id" in update_data:
        terminal_id = update_data["terminal_id"]
        if terminal_id is not None and not session.get(
            CompanyTerminal, terminal_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Terminal not found",
            )
        if allowed_terminal_ids and terminal_id not in allowed_terminal_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this terminal",
            )

    for field, value in update_data.items():
        setattr(equipment, field, value)

    session.add(equipment)
    session.commit()
    session.refresh(equipment)

    if component_serials is not None:
        _replace_component_serials(
            session,
            equipment.id,
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
                EquipmentMeasureSpec.equipment_id == equipment.id
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
                    equipment_id=equipment.id,
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
            EquipmentMeasureSpec.equipment_id == equipment.id
        )
    ).all()
    response.measure_specs = [
        EquipmentMeasureSpecRead(**s.model_dump())
        for s in measure_specs
    ]
    response.component_serials = _get_component_serials(session, equipment.id)
    return response


@router.delete(
    "/{equipment_id}",
    response_model=EquipmentDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_equipment(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentDeleteResponse:
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

    has_inspection = session.exec(
        select(EquipmentInspection.id).where(
            EquipmentInspection.equipment_id == equipment.id
        )
    ).first()
    has_reading = session.exec(
        select(EquipmentReading.id).where(
            EquipmentReading.equipment_id == equipment.id
        )
    ).first()
    has_calibration = session.exec(
        select(EquipmentCalibration.id).where(
            EquipmentCalibration.equipment_id == equipment.id
        )
    ).first()

    if has_inspection or has_reading or has_calibration:
        equipment.is_active = False
        session.add(equipment)
        session.commit()
        session.refresh(equipment)
        response = EquipmentReadWithIncludes.model_validate(equipment, from_attributes=True)
        response.equipment_type = session.get(
            EquipmentType, equipment.equipment_type_id
        )
        response.owner_company = session.get(
            Company, equipment.owner_company_id
        )
        response.terminal = session.get(
            CompanyTerminal, equipment.terminal_id
        )
        response.component_serials = _get_component_serials(session, equipment.id)
        return EquipmentDeleteResponse(
            action="deactivated",
            message="Equipment has operations. It was marked inactive instead of deleted.",
            equipment=response,
        )

    equipment_data = EquipmentReadWithIncludes.model_validate(
        equipment, from_attributes=True
    )
    equipment_data.equipment_type = session.get(
        EquipmentType, equipment.equipment_type_id
    )
    equipment_data.owner_company = session.get(
        Company, equipment.owner_company_id
    )
    equipment_data.terminal = session.get(
        CompanyTerminal, equipment.terminal_id
    )
    equipment_data.component_serials = _get_component_serials(session, equipment.id)

    session.exec(
        delete(EquipmentComponentSerial).where(
            EquipmentComponentSerial.equipment_id == equipment.id
        )
    )
    session.exec(
        delete(EquipmentMeasureSpec).where(
            EquipmentMeasureSpec.equipment_id == equipment.id
        )
    )
    session.exec(
        delete(EquipmentTypeHistory).where(
            EquipmentTypeHistory.equipment_id == equipment.id
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
)
def list_equipment_type_history(
    equipment_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> Any:
    equipment = session.get(Equipment, equipment_id)
    if not equipment:
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

    items = [
        EquipmentTypeHistoryRead(**h.model_dump())
        for h in history
    ]
    return EquipmentTypeHistoryListResponse(items=items)






