from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import InspectionResponseType


class EquipmentVerification(SQLModel, table=True):
    __tablename__ = "equipment_verification"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")
    verification_type_id: int = Field(
        foreign_key="equipment_type_verification.id"
    )
    verified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    created_by_user_id: int = Field(foreign_key="user.id")
    notes: str | None = None
    is_ok: bool | None = None


class EquipmentVerificationResponse(SQLModel, table=True):
    __tablename__ = "equipment_verification_response"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)
    verification_id: int = Field(foreign_key="equipment_verification.id")
    verification_item_id: int = Field(
        foreign_key="equipment_type_verification_item.id"
    )
    response_type: InspectionResponseType
    value_bool: bool | None = None
    value_text: str | None = None
    value_number: float | None = None
    is_ok: bool | None = None


class EquipmentVerificationResponseCreate(SQLModel):
    verification_item_id: int
    response_type: InspectionResponseType
    value_bool: bool | None = None
    value_text: str | None = None
    value_number: float | None = None


class EquipmentVerificationCreate(SQLModel):
    verification_type_id: int | None = None
    verified_at: datetime | None = None
    notes: str | None = None
    reference_equipment_id: int | None = None
    reading_under_test_f: float | None = None
    reference_reading_f: float | None = None
    reading_under_test_value: float | None = None
    reading_under_test_unit: str | None = None
    reference_reading_value: float | None = None
    reference_reading_unit: str | None = None
    reading_under_test_high_value: float | None = None
    reading_under_test_mid_value: float | None = None
    reading_under_test_low_value: float | None = None
    reference_reading_high_value: float | None = None
    reference_reading_mid_value: float | None = None
    reference_reading_low_value: float | None = None
    responses: list[EquipmentVerificationResponseCreate] = Field(
        default_factory=list
    )


class EquipmentVerificationUpdate(SQLModel):
    verification_type_id: int | None = None
    verified_at: datetime | None = None
    notes: str | None = None
    reference_equipment_id: int | None = None
    reading_under_test_f: float | None = None
    reference_reading_f: float | None = None
    reading_under_test_value: float | None = None
    reading_under_test_unit: str | None = None
    reference_reading_value: float | None = None
    reference_reading_unit: str | None = None
    reading_under_test_high_value: float | None = None
    reading_under_test_mid_value: float | None = None
    reading_under_test_low_value: float | None = None
    reference_reading_high_value: float | None = None
    reference_reading_mid_value: float | None = None
    reference_reading_low_value: float | None = None
    responses: list[EquipmentVerificationResponseCreate] = Field(
        default_factory=list
    )


class EquipmentVerificationResponseRead(SQLModel):
    id: int
    verification_id: int
    verification_item_id: int
    response_type: InspectionResponseType
    value_bool: bool | None
    value_text: str | None
    value_number: float | None
    is_ok: bool | None


class EquipmentVerificationRead(SQLModel):
    id: int
    equipment_id: int
    verification_type_id: int
    verified_at: datetime
    created_by_user_id: int
    notes: str | None
    is_ok: bool | None
    reading_under_test_high_value: float | None = None
    reading_under_test_mid_value: float | None = None
    reading_under_test_low_value: float | None = None
    reference_reading_high_value: float | None = None
    reference_reading_mid_value: float | None = None
    reference_reading_low_value: float | None = None
    reading_under_test_unit: str | None = None
    reference_reading_unit: str | None = None
    responses: list[EquipmentVerificationResponseRead] = Field(
        default_factory=list
    )
    message: str | None = None


class EquipmentVerificationListResponse(SQLModel):
    items: list[EquipmentVerificationRead] = Field(default_factory=list)
    message: str | None = None
