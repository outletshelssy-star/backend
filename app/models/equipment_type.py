from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.enums import EquipmentMeasureType, EquipmentRole
from app.models.equipment_type_inspection_item import (
    EquipmentTypeInspectionItemRead,
)
from app.models.equipment_type_max_error import (
    EquipmentTypeMaxErrorCreate,
    EquipmentTypeMaxErrorRead,
)
from app.models.equipment_type_verification import (
    EquipmentTypeVerificationRead,
)
from app.models.mixins.audit import AuditMixin
from app.models.refs import UserRef


class EquipmentTypeBase(SQLModel):
    name: str = Field(min_length=2, description="Equipment type name")
    role: EquipmentRole = Field(description="Equipment role")
    calibration_days: int = Field(ge=0)
    maintenance_days: int = Field(ge=0)
    inspection_days: int = Field(ge=0)
    observations: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    is_lab: bool = Field(default=False)
    created_by_user_id: int = Field(foreign_key="user.id")


class EquipmentType(AuditMixin, EquipmentTypeBase, table=True):
    __tablename__ = "equipment_type"  # type: ignore[misc]
    __table_args__ = (  # type: ignore[misc]
        UniqueConstraint("name", "role", name="uq_equipment_type_name_role"),
    )
    id: int | None = Field(default=None, primary_key=True)


class EquipmentTypeCreate(SQLModel):
    name: str = Field(min_length=2)
    role: EquipmentRole
    calibration_days: int = Field(ge=0)
    maintenance_days: int = Field(ge=0)
    inspection_days: int = Field(ge=0)
    observations: str | None = None
    is_active: bool = True
    is_lab: bool = False
    measures: list[EquipmentMeasureType] = Field(default_factory=list)
    max_errors: list[EquipmentTypeMaxErrorCreate] = Field(default_factory=list)


class EquipmentTypeUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2)
    role: EquipmentRole | None = None
    calibration_days: int | None = Field(default=None, ge=0)
    maintenance_days: int | None = Field(default=None, ge=0)
    inspection_days: int | None = Field(default=None, ge=0)
    observations: str | None = None
    is_active: bool | None = None
    is_lab: bool | None = None
    measures: list[EquipmentMeasureType] | None = None
    max_errors: list[EquipmentTypeMaxErrorCreate] | None = None


class EquipmentTypeRead(SQLModel):
    id: int
    name: str
    role: EquipmentRole
    calibration_days: int
    maintenance_days: int
    inspection_days: int
    observations: str | None
    is_active: bool
    is_lab: bool
    created_by_user_id: int
    measures: list[EquipmentMeasureType] = Field(default_factory=list)
    max_errors: list[EquipmentTypeMaxErrorRead] = Field(default_factory=list)


class EquipmentTypeReadWithIncludes(EquipmentTypeRead):
    creator: UserRef | None = None
    inspection_items: list[EquipmentTypeInspectionItemRead] = Field(
        default_factory=list
    )
    verification_types: list[EquipmentTypeVerificationRead] = Field(
        default_factory=list
    )


class EquipmentTypeListResponse(SQLModel):
    items: list[EquipmentTypeReadWithIncludes] = Field(default_factory=list)
    message: str | None = None


class EquipmentTypeDeleteResponse(SQLModel):
    action: str
    message: str
    equipment_type: EquipmentTypeReadWithIncludes | None = None
