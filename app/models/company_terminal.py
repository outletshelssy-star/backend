from sqlmodel import Field, SQLModel

from app.models.mixins.audit import AuditMixin
from app.models.refs import CompanyBlockRef, CompanyRef, UserRef


class CompanyTerminalBase(SQLModel):
    name: str = Field(min_length=2, description="Nombre del terminal")
    is_active: bool = Field(default=True)
    block_id: int = Field(foreign_key="company_block.id")
    owner_company_id: int = Field(foreign_key="company.id")
    admin_company_id: int = Field(foreign_key="company.id")
    created_by_user_id: int = Field(foreign_key="user.id")


class CompanyTerminal(AuditMixin, CompanyTerminalBase, table=True):
    __tablename__ = "company_terminal"
    id: int | None = Field(default=None, primary_key=True)


class CompanyTerminalCreate(SQLModel):
    name: str = Field(min_length=2)
    is_active: bool = True
    block_id: int
    owner_company_id: int
    admin_company_id: int


class CompanyTerminalUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2)
    is_active: bool | None = None
    block_id: int | None = None
    owner_company_id: int | None = None
    admin_company_id: int | None = None


class CompanyTerminalRead(SQLModel):
    id: int
    name: str
    is_active: bool
    block_id: int
    owner_company_id: int
    admin_company_id: int
    created_by_user_id: int


class CompanyTerminalReadWithIncludes(CompanyTerminalRead):
    block: CompanyBlockRef | None = None
    owner_company: CompanyRef | None = None
    admin_company: CompanyRef | None = None
    creator: UserRef | None = None


class CompanyTerminalListResponse(SQLModel):
    items: list[CompanyTerminalReadWithIncludes] = Field(default_factory=list)
    message: str | None = None


class CompanyTerminalDeleteResponse(SQLModel):
    action: str
    message: str
    terminal: CompanyTerminalReadWithIncludes | None = None
