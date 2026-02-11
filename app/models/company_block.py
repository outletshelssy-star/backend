from sqlmodel import Field, SQLModel

from app.models.mixins.audit import AuditMixin
from app.models.refs import CompanyRef, CompanyTerminalRef, UserRef


class CompanyBlockBase(SQLModel):
    name: str = Field(min_length=2, description="Nombre del bloque")
    is_active: bool = Field(default=True)
    company_id: int = Field(foreign_key="company.id")
    created_by_user_id: int = Field(foreign_key="user.id")


class CompanyBlock(AuditMixin, CompanyBlockBase, table=True):
    __tablename__ = "company_block"
    id: int | None = Field(default=None, primary_key=True)


class CompanyBlockCreate(SQLModel):
    name: str = Field(min_length=2)
    is_active: bool = True
    company_id: int


class CompanyBlockUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2)
    is_active: bool | None = None
    company_id: int | None = None


class CompanyBlockRead(SQLModel):
    id: int
    name: str
    is_active: bool
    company_id: int
    created_by_user_id: int


class CompanyBlockReadWithIncludes(CompanyBlockRead):
    company: CompanyRef | None = None
    creator: UserRef | None = None
    terminals: list[CompanyTerminalRef] = Field(default_factory=list)


class CompanyBlockListResponse(SQLModel):
    items: list[CompanyBlockReadWithIncludes] = Field(default_factory=list)
    message: str | None = None


class CompanyBlockDeleteResponse(SQLModel):
    action: str
    message: str
    block: CompanyBlockReadWithIncludes | None = None
