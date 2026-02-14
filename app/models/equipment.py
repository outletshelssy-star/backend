from sqlmodel import Field, SQLModel

from app.models.enums import EquipmentStatus
from app.models.equipment_measure_spec import (
    EquipmentMeasureSpecCreate,
    EquipmentMeasureSpecRead,
)
from app.models.mixins.audit import AuditMixin
from app.models.refs import CompanyRef, CompanyTerminalRef, EquipmentTypeRef, UserRef
from app.models.equipment_inspection import EquipmentInspectionRead
from app.models.equipment_verification import EquipmentVerificationRead
from app.models.equipment_calibration import EquipmentCalibrationRead


class EquipmentComponentSerialBase(SQLModel):
    component_name: str = Field(min_length=1, description="Component name")
    serial: str = Field(min_length=1, description="Component serial")


class EquipmentComponentSerial(EquipmentComponentSerialBase, table=True):
    __tablename__ = "equipment_component_serial"
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")


class EquipmentComponentSerialCreate(EquipmentComponentSerialBase):
    pass


class EquipmentComponentSerialRead(EquipmentComponentSerialBase):
    id: int
    equipment_id: int


class EquipmentBase(SQLModel):
    internal_code: str | None = Field(default=None, description="Internal code")
    serial: str = Field(min_length=1, description="Equipment serial")
    model: str = Field(min_length=1, description="Equipment model")
    brand: str = Field(min_length=1, description="Equipment brand")
    status: EquipmentStatus = Field(
        default=EquipmentStatus.in_use,
        description="Equipment status",
    )
    is_active: bool = Field(default=True)
    inspection_days_override: int | None = Field(default=None, ge=0)
    equipment_type_id: int = Field(foreign_key="equipment_type.id")
    owner_company_id: int = Field(foreign_key="company.id")
    terminal_id: int = Field(foreign_key="company_terminal.id")
    created_by_user_id: int = Field(foreign_key="user.id")
    weight_class: str | None = Field(
        default=None,
        description="Weight class (E1, E2, F1, F2, M1, M2, M3).",
        max_length=5,
    )
    nominal_mass_value: float | None = Field(
        default=None,
        description="Nominal mass value.",
    )
    nominal_mass_unit: str | None = Field(
        default=None,
        description="Nominal mass unit (g, mg).",
        max_length=2,
    )
    emp_value: float | None = Field(
        default=None,
        description="Maximum permissible error for the weight.",
    )


class Equipment(AuditMixin, EquipmentBase, table=True):
    __tablename__ = "equipment"
    id: int | None = Field(default=None, primary_key=True)


class EquipmentCreate(SQLModel):
    internal_code: str | None = None
    serial: str = Field(min_length=1)
    model: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    status: EquipmentStatus = EquipmentStatus.in_use
    is_active: bool = True
    inspection_days_override: int | None = None
    equipment_type_id: int
    owner_company_id: int
    terminal_id: int
    component_serials: list[EquipmentComponentSerialCreate] = Field(default_factory=list)
    measure_specs: list[EquipmentMeasureSpecCreate] = Field(default_factory=list)
    weight_class: str | None = None
    nominal_mass_value: float | None = None
    nominal_mass_unit: str | None = None
    emp_value: float | None = None


class EquipmentUpdate(SQLModel):
    internal_code: str | None = None
    serial: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    brand: str | None = Field(default=None, min_length=1)
    status: EquipmentStatus | None = None
    is_active: bool | None = None
    inspection_days_override: int | None = None
    equipment_type_id: int | None = None
    owner_company_id: int | None = None
    terminal_id: int | None = None
    component_serials: list[EquipmentComponentSerialCreate] | None = None
    measure_specs: list[EquipmentMeasureSpecCreate] | None = None
    weight_class: str | None = None
    nominal_mass_value: float | None = None
    nominal_mass_unit: str | None = None
    emp_value: float | None = None


class EquipmentRead(SQLModel):
    id: int
    internal_code: str | None
    serial: str
    model: str
    brand: str
    status: EquipmentStatus
    is_active: bool
    inspection_days_override: int | None
    equipment_type_id: int
    owner_company_id: int
    terminal_id: int
    created_by_user_id: int
    weight_class: str | None
    nominal_mass_value: float | None
    nominal_mass_unit: str | None
    emp_value: float | None
    component_serials: list[EquipmentComponentSerialRead] = Field(default_factory=list)
    measure_specs: list[EquipmentMeasureSpecRead] = Field(default_factory=list)


class EquipmentReadWithIncludes(EquipmentRead):
    equipment_type: EquipmentTypeRef | None = None
    owner_company: CompanyRef | None = None
    terminal: CompanyTerminalRef | None = None
    creator: UserRef | None = None
    inspections: list[EquipmentInspectionRead] = Field(default_factory=list)
    verifications: list[EquipmentVerificationRead] = Field(default_factory=list)
    calibrations: list[EquipmentCalibrationRead] = Field(default_factory=list)


class EquipmentListResponse(SQLModel):
    items: list[EquipmentReadWithIncludes] = Field(default_factory=list)
    message: str | None = None


class EquipmentDeleteResponse(SQLModel):
    action: str
    message: str
    equipment: EquipmentReadWithIncludes | None = None
