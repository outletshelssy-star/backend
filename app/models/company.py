from pydantic import field_validator
from sqlmodel import Field, SQLModel

from app.models.enums import CompanyType
from app.models.mixins.audit import AuditMixin
from app.models.refs import CompanyBlockRef, CompanyTerminalRef, UserRef


def _normalize_title(value: str) -> str:
    normalized = " ".join(str(value).strip().lower().split())
    if not normalized:
        return normalized
    return " ".join(word[:1].upper() + word[1:] for word in normalized.split(" "))


class CompanyBase(SQLModel):
    name: str = Field(min_length=2, description="Nombre de la empresa")
    company_type: CompanyType = Field(description="Tipo de empresa")
    is_active: bool = Field(default=True)
    created_by_user_id: int = Field(foreign_key="user.id")


class Company(AuditMixin, CompanyBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class CompanyCreate(SQLModel):
    name: str = Field(min_length=2)
    company_type: CompanyType
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return _normalize_title(v)


class CompanyUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2)
    company_type: CompanyType | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _normalize_title(v)


class CompanyRead(SQLModel):
    id: int
    name: str
    company_type: CompanyType
    is_active: bool
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
