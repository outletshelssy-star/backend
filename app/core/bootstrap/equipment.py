from sqlmodel import Session, select

from app.core.bootstrap.data import DEFAULT_EQUIPMENT, DEFAULT_PRIMARY_COMPANY_NAME
from app.models.company import Company
from app.models.company_terminal import CompanyTerminal
from app.models.enums import (
    EquipmentMeasureType,
    EquipmentRole,
    EquipmentStatus,
    UserType,
)
from app.models.equipment import Equipment
from app.models.equipment import EquipmentComponentSerial
from app.models.equipment_measure_spec import EquipmentMeasureSpec
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_history import EquipmentTypeHistory
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


def ensure_default_equipment(session: Session) -> None:
    company = session.exec(
        select(Company).where(Company.name == DEFAULT_PRIMARY_COMPANY_NAME)
    ).first()
    if not company or company.id is None:
        raise RuntimeError("Company must exist before equipment")

    default_terminal = session.exec(
        select(CompanyTerminal).where(
            CompanyTerminal.owner_company_id == company.id
        )
    ).first()
    if not default_terminal or default_terminal.id is None:
        # Skip seeding if no terminal exists yet.
        return

    superadmin = session.exec(
        select(User).where(User.user_type == UserType.superadmin)
    ).first()
    if not superadmin or superadmin.id is None:
        raise RuntimeError("Superadmin must exist before equipment")

    for data in DEFAULT_EQUIPMENT:
        existing = session.exec(
            select(Equipment).where(Equipment.serial == data["serial"])
        ).first()
        if existing:
            continue

        target = data["equipment_type"]
        equipment_type = session.exec(
            select(EquipmentType).where(
                EquipmentType.name == target["name"],
                EquipmentType.role == EquipmentRole(target["role"]),
            )
        ).first()
        if not equipment_type or equipment_type.id is None:
            continue

        terminal = default_terminal
        terminal_name = data.get("terminal")
        if terminal_name:
            terminal = session.exec(
                select(CompanyTerminal).where(
                    CompanyTerminal.owner_company_id == company.id,
                    CompanyTerminal.name == terminal_name,
                )
            ).first() or default_terminal

        equipment = Equipment(
            serial=data["serial"],
            model=data["model"],
            brand=data["brand"],
            status=EquipmentStatus(data["status"]),
            is_active=True,
            inspection_days_override=data.get("inspection_days_override"),
            equipment_type_id=equipment_type.id,
            company_id=company.id,
            owner_company_id=company.id,
            terminal_id=terminal.id,
            created_by_user_id=superadmin.id,
        )
        session.add(equipment)
        session.commit()
        session.refresh(equipment)
        if equipment.id is None:
            raise RuntimeError("Equipment must have an ID after creation")

        session.add(
            EquipmentTypeHistory(
                equipment_id=equipment.id,
                equipment_type_id=equipment_type.id,
                changed_by_user_id=superadmin.id,
            )
        )
        session.commit()

        for spec in data.get("measure_specs", []):
            measure = EquipmentMeasureType(spec["measure"])
            min_unit = spec["min_unit"]
            max_unit = spec["max_unit"]
            resolution_unit = spec["resolution_unit"]
            min_value = spec["min_value"]
            max_value = spec["max_value"]
            resolution = spec.get("resolution")
            if measure == EquipmentMeasureType.temperature:
                min_norm = _normalize_temperature(min_value, min_unit)
                max_norm = _normalize_temperature(max_value, max_unit)
                res_norm = (
                    _normalize_temperature(resolution, resolution_unit)
                    if resolution is not None
                    else None
                )
            elif measure == EquipmentMeasureType.weight:
                min_norm = _normalize_weight(min_value, min_unit)
                max_norm = _normalize_weight(max_value, max_unit)
                res_norm = (
                    _normalize_weight(resolution, resolution_unit)
                    if resolution is not None
                    else None
                )
            elif measure == EquipmentMeasureType.length:
                min_norm = _normalize_length(min_value, min_unit)
                max_norm = _normalize_length(max_value, max_unit)
                res_norm = (
                    _normalize_length(resolution, resolution_unit)
                    if resolution is not None
                    else None
                )
            else:
                raise ValueError(f"Unit conversion not implemented for {measure}")

            session.add(
                EquipmentMeasureSpec(
                    equipment_id=equipment.id,
                    measure=measure,
                    min_value=min_norm,
                    max_value=max_norm,
                    resolution=res_norm,
                )
            )
        for component in data.get("component_serials", []):
            session.add(
                EquipmentComponentSerial(
                    equipment_id=equipment.id,
                    component_name=component["component_name"],
                    serial=component["serial"],
                )
            )
        session.commit()
