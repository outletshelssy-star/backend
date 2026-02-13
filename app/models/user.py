from __future__ import annotations

from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from sqlmodel import Field, SQLModel

from app.core.security.password import hash_password
from app.core.validators.urls import validate_url
from app.models.enums import UserType
from app.models.refs import CompanyRef, CompanyTerminalRef
from app.models.mixins.audit import AuditMixin


class UserBase(SQLModel):
    name: str = Field(
        min_length=2,
        description="Nombre del Usuario (minimo 2 caracteres)",
    )
    last_name: str = Field(
        min_length=2,
        description="Apellido del usuario (minimo 2 caracteres)",
    )
    email: EmailStr = Field(
        index=True,
        unique=True,
        description="Correo electronico del usuario",
    )
    user_type: UserType = Field(
        default=UserType.user,
        description="Tipo de usuario",
    )
    photo_url: str | None = None
    is_active: bool = Field(default=True)

    @field_validator("name", "last_name")
    @classmethod
    def normalize_names(cls, v: str) -> str:
        normalized = " ".join(str(v).strip().lower().split())
        if not normalized:
            return normalized
        return " ".join(word[:1].upper() + word[1:] for word in normalized.split(" "))

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()

    @field_validator("photo_url")
    @classmethod
    def photo_url_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_url(v)


class User(AuditMixin, UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    password_hash: str = Field(nullable=False)
    refresh_token_hash: str | None = None
    token_version: int = Field(default=0)
    company_id: int | None = Field(default=None, foreign_key="company.id")


class UserCreate(UserBase):
    password: str = Field(min_length=8)
    company_id: int
    terminal_ids: list[int] = Field(default_factory=list)

    def to_user(self) -> User:
        return User(
            **self.model_dump(exclude={"password"}),
            password_hash=hash_password(self.password),
        )


class UserUpdateMe(SQLModel):
    name: str | None = Field(default=None, min_length=2)
    last_name: str | None = Field(default=None, min_length=2)
    photo_url: HttpUrl | None = None

    @field_validator("photo_url")
    @classmethod
    def photo_url_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_url(v)

    @field_validator("name", "last_name")
    @classmethod
    def normalize_names(cls, v: str | None) -> str | None:
        if v is None:
            return v
        normalized = " ".join(str(v).strip().lower().split())
        if not normalized:
            return normalized
        return " ".join(word[:1].upper() + word[1:] for word in normalized.split(" "))


class UserUpdateAdmin(SQLModel):
    name: str | None = Field(
        default=None,
        min_length=2,
    )
    last_name: str | None = Field(
        default=None,
        min_length=2,
    )
    email: EmailStr | None = None
    user_type: UserType | None = None
    photo_url: HttpUrl | None = None
    is_active: bool | None = None
    company_id: int | None = None
    terminal_ids: list[int] | None = None

    @field_validator("photo_url")
    @classmethod
    def photo_url_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_url(v)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr | None) -> str | None:
        if v is None:
            return v
        return str(v).strip().lower()

    @field_validator("name", "last_name")
    @classmethod
    def normalize_names(cls, v: str | None) -> str | None:
        if v is None:
            return v
        normalized = " ".join(str(v).strip().lower().split())
        if not normalized:
            return normalized
        return " ".join(word[:1].upper() + word[1:] for word in normalized.split(" "))


class UserRead(SQLModel):
    id: int
    name: str
    last_name: str
    email: EmailStr
    user_type: UserType
    photo_url: HttpUrl | None
    is_active: bool
    company_id: int | None
    terminal_ids: list[int] = Field(default_factory=list)


class UserReadWithCompany(UserRead):
    company: CompanyRef | None = None
    terminals: list[CompanyTerminalRef] = Field(default_factory=list)


class UserListResponse(SQLModel):
    items: list[UserReadWithCompany] = Field(default_factory=list)
    message: str | None = None


class UserDeleteResponse(SQLModel):
    action: str
    message: str
    user: UserReadWithCompany | None = None


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)
