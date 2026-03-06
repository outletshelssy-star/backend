from sqlmodel import Field, SQLModel

from app.models.enums import EquipmentMeasureType


class EquipmentTypeMaxError(SQLModel, table=True):
    __tablename__ = "equipment_type_max_error"
    id: int | None = Field(default=None, primary_key=True)
    equipment_type_id: int = Field(foreign_key="equipment_type.id")
    measure: EquipmentMeasureType
    max_error_value: float = Field(ge=0)


class EquipmentTypeMaxErrorCreate(SQLModel):
    measure: EquipmentMeasureType
    max_error_value: float
    unit: str


class EquipmentTypeMaxErrorRead(SQLModel):
    id: int
    equipment_type_id: int
    measure: EquipmentMeasureType
    max_error_value: float
