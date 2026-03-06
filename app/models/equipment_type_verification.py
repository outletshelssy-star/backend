from sqlmodel import Field, SQLModel


class EquipmentTypeVerification(SQLModel, table=True):
    __tablename__ = "equipment_type_verification"
    id: int | None = Field(default=None, primary_key=True)
    equipment_type_id: int = Field(foreign_key="equipment_type.id")
    name: str = Field(min_length=2)
    frequency_days: int = Field(ge=0)
    is_active: bool = Field(default=True)
    order: int = Field(default=0)


class EquipmentTypeVerificationCreate(SQLModel):
    name: str = Field(min_length=2)
    frequency_days: int = Field(ge=0)
    is_active: bool = True
    order: int = 0


class EquipmentTypeVerificationUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2)
    frequency_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    order: int | None = None


class EquipmentTypeVerificationRead(SQLModel):
    id: int
    equipment_type_id: int
    name: str
    frequency_days: int
    is_active: bool
    order: int


class EquipmentTypeVerificationListResponse(SQLModel):
    items: list[EquipmentTypeVerificationRead] = Field(default_factory=list)
    message: str | None = None
