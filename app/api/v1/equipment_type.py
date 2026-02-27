from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.enums import EquipmentMeasureType, UserType
from app.models.equipment_type import (
    EquipmentType,
    EquipmentTypeCreate,
    EquipmentTypeDeleteResponse,
    EquipmentTypeListResponse,
    EquipmentTypeReadWithIncludes,
    EquipmentTypeUpdate,
)
from app.models.equipment_type_history import EquipmentTypeHistory
from app.models.equipment_type_inspection_item import (
    EquipmentTypeInspectionItem,
    EquipmentTypeInspectionItemRead,
)
from app.models.equipment_type_max_error import (
    EquipmentTypeMaxError,
    EquipmentTypeMaxErrorCreate,
    EquipmentTypeMaxErrorRead,
)
from app.models.equipment_type_measure import EquipmentTypeMeasure
from app.models.equipment_type_role_history import EquipmentTypeRoleHistory
from app.models.equipment_type_verification import (
    EquipmentTypeVerification,
    EquipmentTypeVerificationRead,
)
from app.models.equipment_type_verification_item import EquipmentTypeVerificationItem
from app.models.refs import UserRef
from app.models.user import User
from app.utils.measurements.length import Length
from app.utils.measurements.temperature import Temperature
from app.utils.measurements.weight import Weight

router = APIRouter(
    prefix="/equipment-types",
    tags=["Equipment Types"],
)


def _require_id(value: int | None, label: str) -> int:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{label} has no ID",
        )
    return value


def _to_user_ref(user: User) -> UserRef:
    return UserRef(
        id=_require_id(user.id, "User"),
        name=user.name,
        last_name=user.last_name,
        email=user.email,
        user_type=user.user_type,
    )


@router.post(
    "/",
    response_model=EquipmentTypeReadWithIncludes,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_400_BAD_REQUEST: {"description": "Solicitud inválida"},
    },
)
def create_equipment_type(
    equipment_type_in: EquipmentTypeCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeReadWithIncludes:
    """
    Crea un tipo de equipo con medidas y errores máximos.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 400: solicitud inválida.
    - 403: permisos insuficientes.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    measures_list = equipment_type_in.measures
    measures_set = set(measures_list)
    if len(measures_list) != len(measures_set):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Measures list contains duplicates",
        )
    max_error_measures = [m.measure for m in equipment_type_in.max_errors]
    if len(max_error_measures) != len(set(max_error_measures)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_errors list contains duplicate measures",
        )
    if measures_set != set(max_error_measures):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_errors must include exactly one entry per measure",
        )

    equipment_type = EquipmentType(
        name=equipment_type_in.name,
        role=equipment_type_in.role,
        calibration_days=equipment_type_in.calibration_days,
        maintenance_days=equipment_type_in.maintenance_days,
        inspection_days=equipment_type_in.inspection_days,
        observations=equipment_type_in.observations,
        is_active=equipment_type_in.is_active,
        is_lab=equipment_type_in.is_lab,
        created_by_user_id=current_user.id,
    )

    session.add(equipment_type)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equipment type with this name and role already exists",
        ) from None
    session.refresh(equipment_type)
    equipment_type_id = _require_id(equipment_type.id, "EquipmentType")

    for measure in equipment_type_in.measures:
        session.add(
            EquipmentTypeMeasure(
                equipment_type_id=equipment_type_id,
                measure=measure,
            )
        )
    session.commit()

    for max_error in equipment_type_in.max_errors:
        if max_error.measure == EquipmentMeasureType.temperature:
            unit_key = max_error.unit.strip().lower()
            try:
                if unit_key in {"c", "celsius"}:
                    normalized_value = Temperature.from_celsius(
                        max_error.max_error_value
                    ).as_celsius
                elif unit_key in {"f", "fahrenheit"}:
                    normalized_value = Temperature.from_fahrenheit(
                        max_error.max_error_value
                    ).as_celsius
                elif unit_key in {"k", "kelvin"}:
                    normalized_value = Temperature.from_kelvin(
                        max_error.max_error_value
                    ).as_celsius
                elif unit_key in {"r", "rankine"}:
                    normalized_value = Temperature.from_rankine(
                        max_error.max_error_value
                    ).as_celsius
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unsupported temperature unit",
                    )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
        elif max_error.measure == EquipmentMeasureType.weight:
            unit_key = max_error.unit.strip().lower()
            try:
                if unit_key in {"g", "gram", "grams"}:
                    normalized_value = Weight.from_grams(
                        max_error.max_error_value
                    ).as_grams
                elif unit_key in {"kg", "kilogram", "kilograms"}:
                    normalized_value = Weight.from_kilograms(
                        max_error.max_error_value
                    ).as_grams
                elif unit_key in {"lb", "lbs", "pound", "pounds"}:
                    normalized_value = Weight.from_pounds(
                        max_error.max_error_value
                    ).as_grams
                elif unit_key in {"oz", "ounce", "ounces"}:
                    normalized_value = Weight.from_ounces(
                        max_error.max_error_value
                    ).as_grams
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unsupported weight unit",
                    )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
        elif max_error.measure == EquipmentMeasureType.length:
            unit_key = max_error.unit.strip().lower()
            try:
                if unit_key in {"mm", "millimeter", "millimeters"}:
                    normalized_value = Length.from_millimeters(
                        max_error.max_error_value
                    ).as_millimeters
                elif unit_key in {"cm", "centimeter", "centimeters"}:
                    normalized_value = Length.from_centimeters(
                        max_error.max_error_value
                    ).as_millimeters
                elif unit_key in {"m", "meter", "meters"}:
                    normalized_value = Length.from_meters(
                        max_error.max_error_value
                    ).as_millimeters
                elif unit_key in {"in", "inch", "inches"}:
                    normalized_value = Length.from_inches(
                        max_error.max_error_value
                    ).as_millimeters
                elif unit_key in {"ft", "foot", "feet"}:
                    normalized_value = Length.from_feet(
                        max_error.max_error_value
                    ).as_millimeters
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unsupported length unit",
                    )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
        elif max_error.measure == EquipmentMeasureType.api:
            unit_key = max_error.unit.strip().lower()
            if unit_key not in {"api"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported API unit",
                )
            normalized_value = max_error.max_error_value
        elif max_error.measure == EquipmentMeasureType.percent_pv:
            unit_key = max_error.unit.strip().lower().replace(" ", "")
            if unit_key not in {"%p/v", "%pv", "p/v", "%w/v"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported percent p/v unit",
                )
            normalized_value = max_error.max_error_value
        elif max_error.measure == EquipmentMeasureType.relative_humidity:
            unit_key = max_error.unit.strip().lower().replace(" ", "")
            if unit_key not in {"%", "%rh", "rh", "percent", "relativehumidity"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported relative humidity unit",
                )
            normalized_value = max_error.max_error_value
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit conversion not implemented for this measure",
            )

        session.add(
            EquipmentTypeMaxError(
                equipment_type_id=equipment_type_id,
                measure=max_error.measure,
                max_error_value=normalized_value,
            )
        )
    session.commit()

    session.add(
        EquipmentTypeRoleHistory(
            equipment_type_id=equipment_type_id,
            role=equipment_type.role,
            changed_by_user_id=current_user.id,
        )
    )
    session.commit()

    response = EquipmentTypeReadWithIncludes.model_validate(
        equipment_type,
        from_attributes=True,
    )
    response.measures = equipment_type_in.measures
    max_errors = session.exec(
        select(EquipmentTypeMaxError).where(
            EquipmentTypeMaxError.equipment_type_id == equipment_type.id
        )
    ).all()
    response.max_errors = [
        EquipmentTypeMaxErrorRead(**m.model_dump()) for m in max_errors
    ]
    return response


@router.get(
    "/",
    response_model=EquipmentTypeListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment_types(
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
    include: str | None = Query(
        default=None,
        description=(
            "Relaciones a incluir, separadas por coma: "
            "`creator`, `inspection_items`, `verification_types`."
        ),
    ),
) -> Any:
    """
    Lista tipos de equipo con relaciones opcionales.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Parámetros:
    - `include`: `creator`, `inspection_items`, `verification_types`.
    """
    equipment_types = session.exec(select(EquipmentType)).all()
    if not equipment_types:
        return EquipmentTypeListResponse(message="No records found")
    include_set = {item.strip() for item in (include or "").split(",") if item.strip()}
    items: list[EquipmentTypeReadWithIncludes] = []
    for equipment_type in equipment_types:
        measures = session.exec(
            select(EquipmentTypeMeasure).where(
                EquipmentTypeMeasure.equipment_type_id == equipment_type.id
            )
        ).all()
        max_errors = session.exec(
            select(EquipmentTypeMaxError).where(
                EquipmentTypeMaxError.equipment_type_id == equipment_type.id
            )
        ).all()
        item = EquipmentTypeReadWithIncludes.model_validate(
            equipment_type,
            from_attributes=True,
        )
        item.measures = [m.measure for m in measures]
        item.max_errors = [
            EquipmentTypeMaxErrorRead(**m.model_dump()) for m in max_errors
        ]
        if include_set:
            if "creator" in include_set:
                creator_db = session.get(User, equipment_type.created_by_user_id)
                if creator_db is not None:
                    item.creator = _to_user_ref(creator_db)
            if "inspection_items" in include_set:
                inspection_items = session.exec(
                    select(EquipmentTypeInspectionItem)
                    .where(
                        EquipmentTypeInspectionItem.equipment_type_id
                        == equipment_type.id
                    )
                    .order_by(EquipmentTypeInspectionItem.order)  # type: ignore[arg-type]
                ).all()
                item.inspection_items = [
                    EquipmentTypeInspectionItemRead(**i.model_dump())
                    for i in inspection_items
                ]
            if "verification_types" in include_set:
                verification_types = session.exec(
                    select(EquipmentTypeVerification)
                    .where(
                        EquipmentTypeVerification.equipment_type_id == equipment_type.id
                    )
                    .order_by(EquipmentTypeVerification.order)  # type: ignore[arg-type]
                ).all()
                item.verification_types = [
                    EquipmentTypeVerificationRead(**v.model_dump())
                    for v in verification_types
                ]
        items.append(item)
    return EquipmentTypeListResponse(items=items)


@router.get(
    "/{equipment_type_id}",
    response_model=EquipmentTypeReadWithIncludes,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def get_equipment_type(
    equipment_type_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
    include: str | None = Query(
        default=None,
        description=(
            "Relaciones a incluir, separadas por coma: "
            "`inspection_items`, `verification_types`, `max_errors`."
        ),
    ),
) -> EquipmentTypeReadWithIncludes:
    """
    Obtiene un tipo de equipo por ID.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Parámetros:
    - `include`: `inspection_items`, `verification_types`, `max_errors`.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    measures = session.exec(
        select(EquipmentTypeMeasure).where(
            EquipmentTypeMeasure.equipment_type_id == equipment_type.id
        )
    ).all()
    max_errors = session.exec(
        select(EquipmentTypeMaxError).where(
            EquipmentTypeMaxError.equipment_type_id == equipment_type.id
        )
    ).all()
    response = EquipmentTypeReadWithIncludes.model_validate(
        equipment_type,
        from_attributes=True,
    )
    response.measures = [m.measure for m in measures]
    response.max_errors = [
        EquipmentTypeMaxErrorRead(**m.model_dump()) for m in max_errors
    ]
    include_set = {item.strip() for item in (include or "").split(",") if item.strip()}
    if include_set:
        if "creator" in include_set:
            creator_db = session.get(User, equipment_type.created_by_user_id)
            if creator_db is not None:
                response.creator = _to_user_ref(creator_db)
        if "inspection_items" in include_set:
            inspection_items = session.exec(
                select(EquipmentTypeInspectionItem)
                .where(
                    EquipmentTypeInspectionItem.equipment_type_id == equipment_type.id
                )
                .order_by(EquipmentTypeInspectionItem.order)  # type: ignore[arg-type]
            ).all()
            response.inspection_items = [
                EquipmentTypeInspectionItemRead(**i.model_dump())
                for i in inspection_items
            ]
        if "verification_types" in include_set:
            verification_types = session.exec(
                select(EquipmentTypeVerification)
                .where(EquipmentTypeVerification.equipment_type_id == equipment_type.id)
                .order_by(EquipmentTypeVerification.order)  # type: ignore[arg-type]
            ).all()
            response.verification_types = [
                EquipmentTypeVerificationRead(**v.model_dump())
                for v in verification_types
            ]
    return response


@router.put(
    "/{equipment_type_id}",
    response_model=EquipmentTypeReadWithIncludes,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_400_BAD_REQUEST: {"description": "Solicitud inválida"},
    },
)
def update_equipment_type(
    equipment_type_id: int,
    equipment_type_in: EquipmentTypeUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeReadWithIncludes:
    """
    Actualiza un tipo de equipo por ID.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 400: solicitud inválida.
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )

    update_data = equipment_type_in.model_dump(exclude_unset=True)

    measures = update_data.get("measures")
    max_errors = update_data.get("max_errors")

    if measures is not None or max_errors is not None:
        if measures is None or max_errors is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="measures and max_errors must be provided together",
            )

        measures_set = set(measures)
        if len(measures) != len(measures_set):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Measures list contains duplicates",
            )
        max_errors = [
            EquipmentTypeMaxErrorCreate.model_validate(m) if isinstance(m, dict) else m
            for m in max_errors
        ]
        max_error_measures = [m.measure for m in max_errors]
        if len(max_error_measures) != len(set(max_error_measures)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_errors list contains duplicate measures",
            )
        if measures_set != set(max_error_measures):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_errors must include exactly one entry per measure",
            )

        existing_measures = session.exec(
            select(EquipmentTypeMeasure).where(
                EquipmentTypeMeasure.equipment_type_id == equipment_type.id
            )
        ).all()
        for measure_item in existing_measures:
            session.delete(measure_item)
        existing_max_errors = session.exec(
            select(EquipmentTypeMaxError).where(
                EquipmentTypeMaxError.equipment_type_id == equipment_type.id
            )
        ).all()
        for max_error_item in existing_max_errors:
            session.delete(max_error_item)
        session.commit()

        for measure in measures:
            session.add(
                EquipmentTypeMeasure(
                    equipment_type_id=_require_id(
                        equipment_type.id, "EquipmentType"
                    ),
                    measure=measure,
                )
            )
        session.commit()

        for max_error in max_errors:
            if max_error.measure == EquipmentMeasureType.temperature:
                unit_key = max_error.unit.strip().lower()
                try:
                    if unit_key in {"c", "celsius"}:
                        normalized_value = Temperature.from_celsius(
                            max_error.max_error_value
                        ).as_celsius
                    elif unit_key in {"f", "fahrenheit"}:
                        normalized_value = Temperature.from_fahrenheit(
                            max_error.max_error_value
                        ).as_celsius
                    elif unit_key in {"k", "kelvin"}:
                        normalized_value = Temperature.from_kelvin(
                            max_error.max_error_value
                        ).as_celsius
                    elif unit_key in {"r", "rankine"}:
                        normalized_value = Temperature.from_rankine(
                            max_error.max_error_value
                        ).as_celsius
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unsupported temperature unit",
                        )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(exc),
                    ) from exc
            elif max_error.measure == EquipmentMeasureType.weight:
                unit_key = max_error.unit.strip().lower()
                try:
                    if unit_key in {"g", "gram", "grams"}:
                        normalized_value = Weight.from_grams(
                            max_error.max_error_value
                        ).as_grams
                    elif unit_key in {"kg", "kilogram", "kilograms"}:
                        normalized_value = Weight.from_kilograms(
                            max_error.max_error_value
                        ).as_grams
                    elif unit_key in {"lb", "lbs", "pound", "pounds"}:
                        normalized_value = Weight.from_pounds(
                            max_error.max_error_value
                        ).as_grams
                    elif unit_key in {"oz", "ounce", "ounces"}:
                        normalized_value = Weight.from_ounces(
                            max_error.max_error_value
                        ).as_grams
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unsupported weight unit",
                        )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(exc),
                    ) from exc
            elif max_error.measure == EquipmentMeasureType.length:
                unit_key = max_error.unit.strip().lower()
                try:
                    if unit_key in {"mm", "millimeter", "millimeters"}:
                        normalized_value = Length.from_millimeters(
                            max_error.max_error_value
                        ).as_millimeters
                    elif unit_key in {"cm", "centimeter", "centimeters"}:
                        normalized_value = Length.from_centimeters(
                            max_error.max_error_value
                        ).as_millimeters
                    elif unit_key in {"m", "meter", "meters"}:
                        normalized_value = Length.from_meters(
                            max_error.max_error_value
                        ).as_millimeters
                    elif unit_key in {"in", "inch", "inches"}:
                        normalized_value = Length.from_inches(
                            max_error.max_error_value
                        ).as_millimeters
                    elif unit_key in {"ft", "foot", "feet"}:
                        normalized_value = Length.from_feet(
                            max_error.max_error_value
                        ).as_millimeters
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unsupported length unit",
                        )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(exc),
                    ) from exc
            elif max_error.measure == EquipmentMeasureType.api:
                unit_key = max_error.unit.strip().lower()
                if unit_key not in {"api"}:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unsupported API unit",
                    )
                normalized_value = max_error.max_error_value
            elif max_error.measure == EquipmentMeasureType.percent_pv:
                unit_key = max_error.unit.strip().lower().replace(" ", "")
                if unit_key not in {"%p/v", "%pv", "p/v", "%w/v"}:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unsupported percent p/v unit",
                    )
                normalized_value = max_error.max_error_value
            elif max_error.measure == EquipmentMeasureType.relative_humidity:
                unit_key = max_error.unit.strip().lower().replace(" ", "")
                if unit_key not in {"%", "%rh", "rh", "percent", "relativehumidity"}:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unsupported relative humidity unit",
                    )
                normalized_value = max_error.max_error_value
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unit conversion not implemented for this measure",
                )

            session.add(
                EquipmentTypeMaxError(
                    equipment_type_id=_require_id(
                        equipment_type.id, "EquipmentType"
                    ),
                    measure=max_error.measure,
                    max_error_value=normalized_value,
                )
            )
        session.commit()

    if "role" in update_data and update_data["role"] != equipment_type.role:
        active_history = session.exec(
            select(EquipmentTypeRoleHistory)
            .where(EquipmentTypeRoleHistory.equipment_type_id == equipment_type.id)
            .where(
                EquipmentTypeRoleHistory.ended_at.is_(None)  # type: ignore[union-attr]
            )
            .order_by(
                EquipmentTypeRoleHistory.started_at.desc()  # type: ignore[attr-defined]
            )
        ).first()
        if active_history:
            active_history.ended_at = datetime.now(UTC)
            session.add(active_history)
            session.commit()

        session.add(
            EquipmentTypeRoleHistory(
                equipment_type_id=_require_id(
                    equipment_type.id, "EquipmentType"
                ),
                role=update_data["role"],
                changed_by_user_id=_require_id(
                    current_user.id, "User"
                ),
            )
        )
        session.commit()

    for field, value in update_data.items():
        if field in {"measures", "max_errors"}:
            continue
        setattr(equipment_type, field, value)

    session.add(equipment_type)
    session.commit()
    session.refresh(equipment_type)

    response = EquipmentTypeReadWithIncludes.model_validate(
        equipment_type,
        from_attributes=True,
    )
    measures_rows = session.exec(
        select(EquipmentTypeMeasure).where(
            EquipmentTypeMeasure.equipment_type_id == equipment_type.id
        )
    ).all()
    response.measures = [m.measure for m in measures_rows]
    max_errors_rows = session.exec(
        select(EquipmentTypeMaxError).where(
            EquipmentTypeMaxError.equipment_type_id == equipment_type.id
        )
    ).all()
    response.max_errors = [
        EquipmentTypeMaxErrorRead(**m.model_dump()) for m in max_errors_rows
    ]
    return response


@router.delete(
    "/{equipment_type_id}",
    response_model=EquipmentTypeDeleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_409_CONFLICT: {"description": "Conflicto: recurso referenciado"},
    },
)
def delete_equipment_type(
    equipment_type_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeDeleteResponse:
    """
    Elimina un tipo de equipo por ID.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    - 409: conflicto por referencias.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )

    equipment_type_data = EquipmentTypeReadWithIncludes.model_validate(
        equipment_type,
        from_attributes=True,
    )

    session.exec(
        delete(EquipmentTypeVerificationItem).where(
            EquipmentTypeVerificationItem.equipment_type_id == equipment_type.id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentTypeVerification).where(
            EquipmentTypeVerification.equipment_type_id == equipment_type.id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentTypeInspectionItem).where(
            EquipmentTypeInspectionItem.equipment_type_id == equipment_type.id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentTypeMeasure).where(
            EquipmentTypeMeasure.equipment_type_id == equipment_type.id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentTypeMaxError).where(
            EquipmentTypeMaxError.equipment_type_id == equipment_type.id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentTypeRoleHistory).where(
            EquipmentTypeRoleHistory.equipment_type_id == equipment_type.id  # type: ignore[arg-type]
        )
    )
    session.exec(
        delete(EquipmentTypeHistory).where(
            EquipmentTypeHistory.equipment_type_id == equipment_type.id  # type: ignore[arg-type]
        )
    )

    session.delete(equipment_type)
    session.commit()

    return EquipmentTypeDeleteResponse(
        action="deleted",
        message="Equipment type deleted successfully.",
        equipment_type=equipment_type_data,
    )
