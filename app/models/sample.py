from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.enums import SampleAnalysisType
from app.models.mixins.audit import AuditMixin


class SampleBase(SQLModel):
    terminal_id: int = Field(foreign_key="company_terminal.id")
    code: str = Field(index=True)
    sequence: int = Field(index=True)
    created_by_user_id: int = Field(foreign_key="user.id")
    identifier: str | None = Field(default=None, max_length=64)
    product_name: str = Field(default="Crudo")
    analyzed_at: datetime | None = None
    thermohygrometer_id: int | None = Field(default=None, foreign_key="equipment.id")
    lab_humidity: float | None = None
    lab_temperature: float | None = None


class Sample(AuditMixin, SampleBase, table=True):
    __tablename__ = "sample"
    id: int | None = Field(default=None, primary_key=True)


class SampleAnalysisBase(SQLModel):
    sample_id: int = Field(foreign_key="sample.id")
    analysis_type: str
    product_name: str = Field(default="Crudo")
    temp_obs_f: float | None = None
    lectura_api: float | None = None
    api_60f: float | None = None
    hydrometer_id: int | None = Field(default=None, foreign_key="equipment.id")
    thermometer_id: int | None = Field(default=None, foreign_key="equipment.id")
    kf_equipment_id: int | None = Field(default=None, foreign_key="equipment.id")
    water_balance_id: int | None = Field(default=None, foreign_key="equipment.id")
    water_value: float | None = None
    water_sample_weight: float | None = None
    water_sample_weight_unit: str | None = Field(default=None, max_length=2)
    water_volume_consumed: float | None = None
    water_volume_unit: str | None = Field(default=None, max_length=2)
    kf_factor_avg: float | None = None


class SampleAnalysis(AuditMixin, SampleAnalysisBase, table=True):
    __tablename__ = "sample_analysis"
    id: int | None = Field(default=None, primary_key=True)


class SampleAnalysisHistoryBase(SQLModel):
    sample_analysis_id: int = Field(foreign_key="sample_analysis.id")
    sample_id: int = Field(foreign_key="sample.id")
    analysis_type: str
    changed_by_user_id: int = Field(foreign_key="user.id")
    product_name_before: str | None = None
    product_name_after: str | None = None
    temp_obs_f_before: float | None = None
    temp_obs_f_after: float | None = None
    lectura_api_before: float | None = None
    lectura_api_after: float | None = None
    api_60f_before: float | None = None
    api_60f_after: float | None = None
    hydrometer_id_before: int | None = Field(default=None, foreign_key="equipment.id")
    hydrometer_id_after: int | None = Field(default=None, foreign_key="equipment.id")
    thermometer_id_before: int | None = Field(default=None, foreign_key="equipment.id")
    thermometer_id_after: int | None = Field(default=None, foreign_key="equipment.id")
    water_value_before: float | None = None
    water_value_after: float | None = None


class SampleAnalysisHistory(AuditMixin, SampleAnalysisHistoryBase, table=True):
    __tablename__ = "sample_analysis_history"
    id: int | None = Field(default=None, primary_key=True)


class SampleAnalysisCreate(SQLModel):
    analysis_type: SampleAnalysisType
    product_name: str = "Crudo"
    temp_obs_f: float | None = None
    lectura_api: float | None = None
    hydrometer_id: int | None = None
    thermometer_id: int | None = None
    kf_equipment_id: int | None = None
    water_balance_id: int | None = None
    water_value: float | None = None
    water_sample_weight: float | None = None
    water_sample_weight_unit: str | None = None
    water_volume_consumed: float | None = None
    water_volume_unit: str | None = None
    kf_factor_avg: float | None = None


class SampleCreate(SQLModel):
    terminal_id: int
    identifier: str
    analyses: list[SampleAnalysisCreate] = Field(default_factory=list)


class SampleAnalysisUpdate(SQLModel):
    id: int | None = None
    analysis_type: SampleAnalysisType
    product_name: str | None = None
    temp_obs_f: float | None = None
    lectura_api: float | None = None
    hydrometer_id: int | None = None
    thermometer_id: int | None = None
    kf_equipment_id: int | None = None
    water_balance_id: int | None = None
    water_value: float | None = None
    water_sample_weight: float | None = None
    water_sample_weight_unit: str | None = None
    water_volume_consumed: float | None = None
    water_volume_unit: str | None = None
    kf_factor_avg: float | None = None


class SampleUpdate(SQLModel):
    product_name: str | None = None
    analyzed_at: datetime | None = None
    thermohygrometer_id: int | None = None
    lab_humidity: float | None = None
    lab_temperature: float | None = None
    identifier: str | None = None
    analyses: list[SampleAnalysisUpdate] | None = None


class SampleAnalysisRead(SQLModel):
    id: int
    sample_id: int
    analysis_type: str
    product_name: str
    temp_obs_f: float | None
    lectura_api: float | None
    api_60f: float | None
    hydrometer_id: int | None
    thermometer_id: int | None
    kf_equipment_id: int | None
    water_value: float | None
    water_sample_weight: float | None
    water_balance_id: int | None
    water_sample_weight_unit: str | None
    water_volume_consumed: float | None
    water_volume_unit: str | None
    kf_factor_avg: float | None


class SampleRead(SQLModel):
    id: int
    terminal_id: int
    code: str
    sequence: int
    created_by_user_id: int
    created_at: datetime
    identifier: str | None
    product_name: str
    analyzed_at: datetime | None
    thermohygrometer_id: int | None = None
    lab_humidity: float | None
    lab_temperature: float | None
    analyses: list[SampleAnalysisRead] = Field(default_factory=list)


class SampleListResponse(SQLModel):
    items: list[SampleRead] = Field(default_factory=list)
    message: str | None = None
