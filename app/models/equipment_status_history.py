from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import EquipmentStatus


class EquipmentStatusHistory(SQLModel, table=True):
    __tablename__ = "equipment_status_history"
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")
    status: EquipmentStatus = Field(description="Equipment status")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Status start time (UTC).",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="Status end time (UTC).",
    )
    changed_by_user_id: int = Field(foreign_key="user.id")


class EquipmentStatusHistoryRead(SQLModel):
    id: int
    equipment_id: int
    status: EquipmentStatus
    started_at: datetime
    ended_at: datetime | None
    changed_by_user_id: int


class EquipmentStatusHistoryListResponse(SQLModel):
    items: list[EquipmentStatusHistoryRead] = Field(default_factory=list)
    message: str | None = None
