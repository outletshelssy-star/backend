from sqlmodel import Field, SQLModel

from app.models.enums import CompanyType
from app.models.mixins.audit import AuditMixin
from app.models.refs import CompanyBlockRef, CompanyTerminalRef, UserRef


class CompanyBase(SQLModel):
    name: str = Field(min_length=2, description="Nombre de la empresa")
    company_type: CompanyType = Field(description="Tipo de empresa")
    created_by_user_id: int = Field(foreign_key="user.id")


class Company(AuditMixin, CompanyBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class CompanyCreate(SQLModel):
    name: str = Field(min_length=2)
    company_type: CompanyType


class CompanyUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2)
    company_type: CompanyType | None = None


class CompanyRead(SQLModel):
    id: int
    name: str
    company_type: CompanyType
    created_by_user_id: int


class CompanyReadWithIncludes(CompanyRead):
    creator: UserRef | None = None
    blocks: list[CompanyBlockRef] = Field(default_factory=list)
    terminals: list[CompanyTerminalRef] = Field(default_factory=list)


class CompanyListResponse(SQLModel):
    items: list[CompanyReadWithIncludes] = Field(default_factory=list)
    message: str | None = None


class CompanyDeleteResponse(SQLModel):
    action: str
    message: str
    company: CompanyReadWithIncludes | None = None
