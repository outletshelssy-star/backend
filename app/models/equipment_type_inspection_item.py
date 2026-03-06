import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.models.enums import InspectionResponseType


class EquipmentTypeInspectionItem(SQLModel, table=True):
    __tablename__ = "equipment_type_inspection_item"
    id: int | None = Field(default=None, primary_key=True)
    equipment_type_id: int = Field(foreign_key="equipment_type.id")
    item: str = Field(min_length=2)
    response_type: InspectionResponseType
    is_required: bool = Field(default=True)
    order: int = Field(default=0)
    expected_bool: bool | None = None
    expected_text_options: list[str] | None = Field(
        default=None, sa_column=sa.Column(sa.JSON)
    )
    expected_number: float | None = None
    expected_number_min: float | None = None
    expected_number_max: float | None = None


class EquipmentTypeInspectionItemCreate(SQLModel):
    item: str = Field(min_length=2)
    response_type: InspectionResponseType
    is_required: bool = True
    order: int = 0
    expected_bool: bool | None = None
    expected_text_options: list[str] | None = None
    expected_number: float | None = None
    expected_number_min: float | None = None
    expected_number_max: float | None = None


class EquipmentTypeInspectionItemRead(SQLModel):
    id: int
    equipment_type_id: int
    item: str
    response_type: InspectionResponseType
    is_required: bool
    order: int
    expected_bool: bool | None
    expected_text_options: list[str] | None
    expected_number: float | None
    expected_number_min: float | None
    expected_number_max: float | None


class EquipmentTypeInspectionItemUpdate(SQLModel):
    item: str | None = Field(default=None, min_length=2)
    response_type: InspectionResponseType | None = None
    is_required: bool | None = None
    order: int | None = None
    expected_bool: bool | None = None
    expected_text_options: list[str] | None = None
    expected_number: float | None = None
    expected_number_min: float | None = None
    expected_number_max: float | None = None


class EquipmentTypeInspectionItemListResponse(SQLModel):
    items: list[EquipmentTypeInspectionItemRead] = Field(default_factory=list)
    message: str | None = None


class EquipmentTypeInspectionItemBulkCreate(SQLModel):
    items: list[EquipmentTypeInspectionItemCreate] = Field(default_factory=list)
