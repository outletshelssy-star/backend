from pydantic import field_validator
from sqlmodel import Field, SQLModel

from app.models.mixins.audit import AuditMixin
from app.models.refs import CompanyBlockRef, CompanyRef, UserRef


def _normalize_title(value: str) -> str:
    normalized = " ".join(str(value).strip().lower().split())
    if not normalized:
        return normalized
    return " ".join(word[:1].upper() + word[1:] for word in normalized.split(" "))


class CompanyTerminalBase(SQLModel):
    name: str = Field(min_length=2, description="Nombre del terminal")
    is_active: bool = Field(default=True)
    block_id: int = Field(foreign_key="company_block.id")
    owner_company_id: int = Field(foreign_key="company.id")
    admin_company_id: int = Field(foreign_key="company.id")
    created_by_user_id: int = Field(foreign_key="user.id")
    terminal_code: str = Field(min_length=3, max_length=4, nullable=False)


class CompanyTerminal(AuditMixin, CompanyTerminalBase, table=True):
    __tablename__ = "company_terminal"
    id: int | None = Field(default=None, primary_key=True)
    next_sample_sequence: int = Field(default=1, nullable=False)


class CompanyTerminalCreate(SQLModel):
    name: str = Field(min_length=2)
    is_active: bool = True
    block_id: int
    owner_company_id: int
    admin_company_id: int
    terminal_code: str = Field(min_length=3, max_length=4)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return _normalize_title(v)

    @field_validator("terminal_code")
    @classmethod
    def normalize_terminal_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        normalized = str(v).strip().upper()
        if not normalized:
            return None
        if not normalized.isalpha() or not (3 <= len(normalized) <= 4):
            raise ValueError("Terminal code must be 3 to 4 letters (A-Z).")
        return normalized


class CompanyTerminalUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2)
    is_active: bool | None = None
    block_id: int | None = None
    owner_company_id: int | None = None
    admin_company_id: int | None = None
    terminal_code: str | None = Field(default=None, min_length=3, max_length=4)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _normalize_title(v)

    @field_validator("terminal_code")
    @classmethod
    def normalize_terminal_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        normalized = str(v).strip().upper()
        if not normalized:
            return None
        if not normalized.isalpha() or not (3 <= len(normalized) <= 4):
            raise ValueError("Terminal code must be 3 to 4 letters (A-Z).")
        return normalized


class CompanyTerminalRead(SQLModel):
    id: int
    name: str
    is_active: bool
    block_id: int
    owner_company_id: int
    admin_company_id: int
    created_by_user_id: int
    next_sample_sequence: int
    terminal_code: str


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
