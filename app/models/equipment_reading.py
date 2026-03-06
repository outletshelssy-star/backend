from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class EquipmentReading(SQLModel, table=True):
    __tablename__ = "equipment_reading"
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")
    value_celsius: float = Field(description="Temperature in Celsius")
    measured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by_user_id: int = Field(foreign_key="user.id")


class EquipmentReadingCreate(SQLModel):
    value: float
    unit: str
    measured_at: datetime | None = None


class EquipmentReadingRead(SQLModel):
    id: int
    equipment_id: int
    value_celsius: float
    measured_at: datetime
    created_by_user_id: int


class EquipmentReadingListResponse(SQLModel):
    items: list[EquipmentReadingRead] = Field(default_factory=list)
    message: str | None = None
