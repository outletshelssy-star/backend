from pydantic import EmailStr
from sqlmodel import SQLModel

from app.models.enums import CompanyType, EquipmentRole, UserType


class UserRef(SQLModel):
    id: int
    name: str
    last_name: str
    email: EmailStr
    user_type: UserType


class CompanyRef(SQLModel):
    id: int
    name: str
    company_type: CompanyType
    is_active: bool


class CompanyBlockRef(SQLModel):
    id: int
    name: str
    is_active: bool


class CompanyTerminalRef(SQLModel):
    id: int
    name: str
    is_active: bool


class EquipmentTypeRef(SQLModel):
    id: int
    name: str
    role: EquipmentRole
    inspection_days: int | None = None
    calibration_days: int | None = None
    is_lab: bool | None = None
