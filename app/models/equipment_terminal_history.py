from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class EquipmentTerminalHistory(SQLModel, table=True):
    __tablename__ = "equipment_terminal_history"
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")
    terminal_id: int = Field(foreign_key="company_terminal.id")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Terminal start time (UTC).",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="Terminal end time (UTC).",
    )
    changed_by_user_id: int = Field(foreign_key="user.id")


class EquipmentTerminalHistoryRead(SQLModel):
    id: int
    equipment_id: int
    terminal_id: int
    started_at: datetime
    ended_at: datetime | None
    changed_by_user_id: int


class EquipmentTerminalHistoryListResponse(SQLModel):
    items: list[EquipmentTerminalHistoryRead] = Field(default_factory=list)
    message: str | None = None
