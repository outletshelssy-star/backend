from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.mixins.audit import AuditMixin


class ExternalAnalysisTerminal(AuditMixin, SQLModel, table=True):
    __tablename__ = "external_analysis_terminal"
    __table_args__ = (
        UniqueConstraint(
            "terminal_id",
            "analysis_type_id",
            name="uq_external_analysis_terminal",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    terminal_id: int = Field(foreign_key="company_terminal.id")
    analysis_type_id: int = Field(foreign_key="external_analysis_type.id")
    frequency_days: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    created_by_user_id: int = Field(foreign_key="user.id")


class ExternalAnalysisTerminalCreate(SQLModel):
    analysis_type_id: int
    frequency_days: int = Field(default=0, ge=0)
    is_active: bool = True


class ExternalAnalysisTerminalUpdate(SQLModel):
    frequency_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ExternalAnalysisTerminalRead(SQLModel):
    terminal_id: int
    analysis_type_id: int
    analysis_type_name: str
    frequency_days: int
    is_active: bool
    last_performed_at: datetime | None = None
    next_due_at: datetime | None = None


class ExternalAnalysisTerminalListResponse(SQLModel):
    items: list[ExternalAnalysisTerminalRead] = Field(default_factory=list)
    message: str | None = None
