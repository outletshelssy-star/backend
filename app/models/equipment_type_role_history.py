from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import EquipmentRole


class EquipmentTypeRoleHistory(SQLModel, table=True):
    __tablename__ = "equipment_type_role_history"
    id: int | None = Field(default=None, primary_key=True)
    equipment_type_id: int = Field(foreign_key="equipment_type.id")
    role: EquipmentRole
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Role start time (UTC).",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="Role end time (UTC).",
    )
    changed_by_user_id: int = Field(foreign_key="user.id")
