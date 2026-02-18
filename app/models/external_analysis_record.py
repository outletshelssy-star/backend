from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.mixins.audit import AuditMixin


class ExternalAnalysisRecord(AuditMixin, SQLModel, table=True):
    __tablename__ = "external_analysis_record"

    id: int | None = Field(default=None, primary_key=True)
    terminal_id: int = Field(foreign_key="company_terminal.id")
    analysis_type_id: int = Field(foreign_key="external_analysis_type.id")
    analysis_company_id: int | None = Field(
        default=None, foreign_key="company.id"
    )
    performed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    report_number: str | None = None
    report_pdf_url: str | None = None
    result_value: float | None = None
    result_unit: str | None = None
    result_uncertainty: float | None = None
    method: str | None = None
    notes: str | None = None
    created_by_user_id: int = Field(foreign_key="user.id")


class ExternalAnalysisRecordCreate(SQLModel):
    analysis_type_id: int
    analysis_company_id: int | None = None
    performed_at: datetime | None = None
    report_number: str | None = None
    result_value: float | None = None
    result_unit: str | None = None
    result_uncertainty: float | None = None
    method: str | None = None
    notes: str | None = None


class ExternalAnalysisRecordUpdate(SQLModel):
    analysis_type_id: int | None = None
    analysis_company_id: int | None = None
    performed_at: datetime | None = None
    report_number: str | None = None
    result_value: float | None = None
    result_unit: str | None = None
    result_uncertainty: float | None = None
    method: str | None = None
    notes: str | None = None


class ExternalAnalysisRecordRead(SQLModel):
    id: int
    terminal_id: int
    analysis_type_id: int
    analysis_type_name: str
    analysis_company_id: int | None
    analysis_company_name: str | None
    performed_at: datetime
    report_number: str | None
    report_pdf_url: str | None
    result_value: float | None
    result_unit: str | None
    result_uncertainty: float | None
    method: str | None
    notes: str | None
    created_by_user_id: int


class ExternalAnalysisRecordListResponse(SQLModel):
    items: list[ExternalAnalysisRecordRead] = Field(default_factory=list)
    message: str | None = None
