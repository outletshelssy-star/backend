from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class EquipmentTypeHistory(SQLModel, table=True):
    __tablename__ = "equipment_type_history"
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")
    equipment_type_id: int = Field(foreign_key="equipment_type.id")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Type start time (UTC).",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="Type end time (UTC).",
    )
    changed_by_user_id: int = Field(foreign_key="user.id")


class EquipmentTypeChange(SQLModel):
    equipment_type_id: int


class EquipmentTypeHistoryRead(SQLModel):
    id: int
    equipment_id: int
    equipment_type_id: int
    started_at: datetime
    ended_at: datetime | None
    changed_by_user_id: int


class EquipmentTypeHistoryListResponse(SQLModel):
    items: list[EquipmentTypeHistoryRead] = Field(default_factory=list)
    message: str | None = None
