from sqlmodel import Field, SQLModel

from app.models.enums import EquipmentMeasureType


class EquipmentTypeMeasure(SQLModel, table=True):
    __tablename__ = "equipment_type_measure"
    id: int | None = Field(default=None, primary_key=True)
    equipment_type_id: int = Field(foreign_key="equipment_type.id")
    measure: EquipmentMeasureType
