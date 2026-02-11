from sqlmodel import Session, select

from app.core.bootstrap.data import (
    DEFAULT_EQUIPMENT_TYPE_INSPECTION_ITEMS,
    DEFAULT_EQUIPMENT_TYPES,
)
from app.models.enums import (
    EquipmentMeasureType,
    EquipmentRole,
    InspectionResponseType,
    UserType,
)
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_inspection_item import EquipmentTypeInspectionItem
from app.models.equipment_type_max_error import EquipmentTypeMaxError
from app.models.equipment_type_measure import EquipmentTypeMeasure
from app.models.equipment_type_verification import EquipmentTypeVerification
from app.models.user import User
from app.utils.measurements.length import Length
from app.utils.measurements.temperature import Temperature
from app.utils.measurements.weight import Weight


def _normalize_temperature(value: float, unit: str) -> float:
    unit_key = unit.strip().lower()
    if unit_key in {"c", "celsius"}:
        return Temperature.from_celsius(value).as_celsius
    if unit_key in {"f", "fahrenheit"}:
        return Temperature.from_fahrenheit(value).as_celsius
    if unit_key in {"k", "kelvin"}:
        return Temperature.from_kelvin(value).as_celsius
    if unit_key in {"r", "rankine"}:
        return Temperature.from_rankine(value).as_celsius
    raise ValueError(f"Unsupported temperature unit: {unit}")


def _normalize_weight(value: float, unit: str) -> float:
    unit_key = unit.strip().lower()
    if unit_key in {"g", "gram", "grams"}:
        return Weight.from_grams(value).as_grams
    if unit_key in {"kg", "kilogram", "kilograms"}:
        return Weight.from_kilograms(value).as_grams
    if unit_key in {"lb", "lbs", "pound", "pounds"}:
        return Weight.from_pounds(value).as_grams
    if unit_key in {"oz", "ounce", "ounces"}:
        return Weight.from_ounces(value).as_grams
    raise ValueError(f"Unsupported weight unit: {unit}")


def _normalize_length(value: float, unit: str) -> float:
    unit_key = unit.strip().lower()
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
    raise ValueError(f"Unsupported length unit: {unit}")


def ensure_default_equipment_types(session: Session) -> None:
    superadmin = session.exec(
        select(User).where(User.user_type == UserType.superadmin)
    ).first()
    if not superadmin or superadmin.id is None:
        raise RuntimeError("Superadmin must exist before equipment types")

    for data in DEFAULT_EQUIPMENT_TYPES:
        existing = session.exec(
            select(EquipmentType).where(
                EquipmentType.name == data["name"],
                EquipmentType.role == EquipmentRole(data["role"]),
            )
        ).first()
        if existing:
            continue

        equipment_type = EquipmentType(
            name=data["name"],
            role=EquipmentRole(data["role"]),
            calibration_days=data["calibration_days"],
            maintenance_days=data["maintenance_days"],
            inspection_days=data["inspection_days"],
            observations=data.get("observations"),
            is_active=True,
            created_by_user_id=superadmin.id,
        )
        session.add(equipment_type)
        session.commit()
        session.refresh(equipment_type)
        if equipment_type.id is None:
            raise RuntimeError("Equipment type must have an ID after creation")

        measures = data.get("measures", [])
        for measure in measures:
            session.add(
                EquipmentTypeMeasure(
                    equipment_type_id=equipment_type.id,
                    measure=EquipmentMeasureType(measure),
                )
            )
        session.commit()

        max_errors = data.get("max_errors", [])
        for item in max_errors:
            measure = EquipmentMeasureType(item["measure"])
            value = item["max_error_value"]
            unit = item["unit"]
            if measure == EquipmentMeasureType.temperature:
                normalized = _normalize_temperature(value, unit)
            elif measure == EquipmentMeasureType.weight:
                normalized = _normalize_weight(value, unit)
            elif measure == EquipmentMeasureType.length:
                normalized = _normalize_length(value, unit)
            else:
                raise ValueError(f"Unit conversion not implemented for {measure}")
            session.add(
                EquipmentTypeMaxError(
                    equipment_type_id=equipment_type.id,
                    measure=measure,
                    max_error_value=normalized,
                )
            )
        session.commit()


def ensure_default_equipment_type_inspection_items(
    session: Session,
) -> None:
    for seed in DEFAULT_EQUIPMENT_TYPE_INSPECTION_ITEMS:
        target = seed["equipment_type"]
        equipment_type = session.exec(
            select(EquipmentType).where(
                EquipmentType.name == target["name"],
                EquipmentType.role == EquipmentRole(target["role"]),
            )
        ).first()
        if not equipment_type or equipment_type.id is None:
            continue

        existing_items = session.exec(
            select(EquipmentTypeInspectionItem).where(
                EquipmentTypeInspectionItem.equipment_type_id == equipment_type.id
            )
        ).all()
        existing_by_text = {item.item: item for item in existing_items}

        for item_data in seed["items"]:
            current = existing_by_text.get(item_data["item"])
            if current:
                current.response_type = InspectionResponseType(item_data["response_type"])
                current.is_required = item_data["is_required"]
                current.order = item_data["order"]
                current.expected_bool = item_data.get("expected_bool")
                current.expected_text_options = item_data.get("expected_text_options")
                current.expected_number = item_data.get("expected_number")
                current.expected_number_min = item_data.get("expected_number_min")
                current.expected_number_max = item_data.get("expected_number_max")
                session.add(current)
                continue
            session.add(
                EquipmentTypeInspectionItem(
                    equipment_type_id=equipment_type.id,
                    item=item_data["item"],
                    response_type=InspectionResponseType(item_data["response_type"]),
                    is_required=item_data["is_required"],
                    order=item_data["order"],
                    expected_bool=item_data.get("expected_bool"),
                    expected_text_options=item_data.get("expected_text_options"),
                    expected_number=item_data.get("expected_number"),
                    expected_number_min=item_data.get("expected_number_min"),
                    expected_number_max=item_data.get("expected_number_max"),
                )
            )
        session.commit()


def ensure_default_equipment_type_verifications(session: Session) -> None:
    for seed in DEFAULT_EQUIPMENT_TYPES:
        target_name = seed["name"]
        target_role = EquipmentRole(seed["role"])
        equipment_type = session.exec(
            select(EquipmentType).where(
                EquipmentType.name == target_name,
                EquipmentType.role == target_role,
            )
        ).first()
        if not equipment_type or equipment_type.id is None:
            continue

        defaults = seed.get("verification_types")
        if not defaults:
            defaults = [
                {
                    "name": "Verificacion",
                    "frequency_days": 0,
                    "is_active": True,
                    "order": 0,
                }
            ]

        existing = session.exec(
            select(EquipmentTypeVerification).where(
                EquipmentTypeVerification.equipment_type_id == equipment_type.id
            )
        ).all()
        existing_by_name = {item.name.strip().lower(): item for item in existing}

        for entry in defaults:
            key = str(entry.get("name", "")).strip().lower()
            if not key:
                continue
            current = existing_by_name.get(key)
            if current:
                current.frequency_days = int(entry.get("frequency_days", 0))
                current.is_active = bool(entry.get("is_active", True))
                current.order = int(entry.get("order", 0))
                session.add(current)
                continue
            session.add(
                EquipmentTypeVerification(
                    equipment_type_id=equipment_type.id,
                    name=str(entry["name"]).strip(),
                    frequency_days=int(entry.get("frequency_days", 0)),
                    is_active=bool(entry.get("is_active", True)),
                    order=int(entry.get("order", 0)),
                )
            )
        session.commit()
