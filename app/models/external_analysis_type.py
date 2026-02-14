from sqlmodel import Field, SQLModel
from sqlalchemy import UniqueConstraint

from app.models.mixins.audit import AuditMixin


class ExternalAnalysisType(AuditMixin, SQLModel, table=True):
    __tablename__ = "external_analysis_type"
    __table_args__ = (UniqueConstraint("name", name="uq_external_analysis_type_name"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    default_frequency_days: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    created_by_user_id: int = Field(foreign_key="user.id")


class ExternalAnalysisTypeCreate(SQLModel):
    name: str
    default_frequency_days: int = Field(default=0, ge=0)
    is_active: bool = True


class ExternalAnalysisTypeUpdate(SQLModel):
    name: str | None = None
    default_frequency_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ExternalAnalysisTypeRead(SQLModel):
    id: int
    name: str
    default_frequency_days: int
    is_active: bool
    created_by_user_id: int


class ExternalAnalysisTypeListResponse(SQLModel):
    items: list[ExternalAnalysisTypeRead] = Field(default_factory=list)
    message: str | None = None
