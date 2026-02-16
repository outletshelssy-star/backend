from datetime import datetime

from sqlmodel import Field, SQLModel


class EquipmentHistoryEntry(SQLModel):
    id: str
    kind: str = Field(description="type | terminal")
    equipment_type_id: int | None = None
    terminal_id: int | None = None
    started_at: datetime
    ended_at: datetime | None
    changed_by_user_id: int
    changed_by_user_name: str | None = None


class EquipmentHistoryListResponse(SQLModel):
    items: list[EquipmentHistoryEntry] = Field(default_factory=list)
    message: str | None = None
