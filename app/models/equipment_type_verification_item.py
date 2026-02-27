import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.models.enums import InspectionResponseType


class EquipmentTypeVerificationItem(SQLModel, table=True):
    __tablename__ = "equipment_type_verification_item"
    id: int | None = Field(default=None, primary_key=True)
    equipment_type_id: int = Field(foreign_key="equipment_type.id")
    verification_type_id: int = Field(foreign_key="equipment_type_verification.id")
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


class EquipmentTypeVerificationItemCreate(SQLModel):
    verification_type_id: int | None = None
    item: str = Field(min_length=2)
    response_type: InspectionResponseType
    is_required: bool = True
    order: int = 0
    expected_bool: bool | None = None
    expected_text_options: list[str] | None = None
    expected_number: float | None = None
    expected_number_min: float | None = None
    expected_number_max: float | None = None


class EquipmentTypeVerificationItemRead(SQLModel):
    id: int
    equipment_type_id: int
    verification_type_id: int
    item: str
    response_type: InspectionResponseType
    is_required: bool
    order: int
    expected_bool: bool | None
    expected_text_options: list[str] | None
    expected_number: float | None
    expected_number_min: float | None
    expected_number_max: float | None


class EquipmentTypeVerificationItemUpdate(SQLModel):
    verification_type_id: int | None = None
    item: str | None = Field(default=None, min_length=2)
    response_type: InspectionResponseType | None = None
    is_required: bool | None = None
    order: int | None = None
    expected_bool: bool | None = None
    expected_text_options: list[str] | None = None
    expected_number: float | None = None
    expected_number_min: float | None = None
    expected_number_max: float | None = None


class EquipmentTypeVerificationItemListResponse(SQLModel):
    items: list[EquipmentTypeVerificationItemRead] = Field(default_factory=list)
    message: str | None = None


class EquipmentTypeVerificationItemBulkCreate(SQLModel):
    items: list[EquipmentTypeVerificationItemCreate] = Field(default_factory=list)
