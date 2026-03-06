from sqlmodel import Field, SQLModel

from app.models.enums import EquipmentMeasureType


class EquipmentMeasureSpec(SQLModel, table=True):
    __tablename__ = "equipment_measure_spec"
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")
    measure: EquipmentMeasureType
    min_value: float | None = Field(default=None)
    max_value: float | None = Field(default=None)
    resolution: float | None = Field(default=None)


class EquipmentMeasureSpecCreate(SQLModel):
    measure: EquipmentMeasureType
    min_unit: str
    max_unit: str
    resolution_unit: str
    min_value: float | None = None
    max_value: float | None = None
    resolution: float | None = None


class EquipmentMeasureSpecRead(SQLModel):
    id: int
    equipment_id: int
    measure: EquipmentMeasureType
    min_value: float | None
    max_value: float | None
    resolution: float | None
