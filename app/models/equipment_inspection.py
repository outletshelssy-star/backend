from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import InspectionResponseType


class EquipmentInspection(SQLModel, table=True):
    __tablename__ = "equipment_inspection"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")
    inspected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    created_by_user_id: int = Field(foreign_key="user.id")
    notes: str | None = None
    is_ok: bool | None = None


class EquipmentInspectionResponse(SQLModel, table=True):
    __tablename__ = "equipment_inspection_response"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)
    inspection_id: int = Field(foreign_key="equipment_inspection.id")
    inspection_item_id: int = Field(
        foreign_key="equipment_type_inspection_item.id"
    )
    response_type: InspectionResponseType
    value_bool: bool | None = None
    value_text: str | None = None
    value_number: float | None = None
    is_ok: bool | None = None


class EquipmentInspectionResponseCreate(SQLModel):
    inspection_item_id: int
    response_type: InspectionResponseType
    value_bool: bool | None = None
    value_text: str | None = None
    value_number: float | None = None


class EquipmentInspectionCreate(SQLModel):
    inspected_at: datetime | None = None
    notes: str | None = None
    responses: list[EquipmentInspectionResponseCreate] = Field(
        default_factory=list
    )


class EquipmentInspectionUpdate(SQLModel):
    inspected_at: datetime | None = None
    notes: str | None = None
    responses: list[EquipmentInspectionResponseCreate] = Field(
        default_factory=list
    )


class EquipmentInspectionResponseRead(SQLModel):
    id: int
    inspection_id: int
    inspection_item_id: int
    response_type: InspectionResponseType
    value_bool: bool | None
    value_text: str | None
    value_number: float | None
    is_ok: bool | None


class EquipmentInspectionRead(SQLModel):
    id: int
    equipment_id: int
    inspected_at: datetime
    created_by_user_id: int
    notes: str | None
    is_ok: bool | None
    responses: list[EquipmentInspectionResponseRead] = Field(
        default_factory=list
    )
    message: str | None = None


class EquipmentInspectionListResponse(SQLModel):
    items: list[EquipmentInspectionRead] = Field(default_factory=list)
    message: str | None = None
