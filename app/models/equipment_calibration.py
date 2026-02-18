from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class EquipmentCalibration(SQLModel, table=True):
    __tablename__ = "equipment_calibration"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)
    equipment_id: int = Field(foreign_key="equipment.id")
    calibrated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    created_by_user_id: int = Field(foreign_key="user.id")
    calibration_company_id: int | None = Field(default=None, foreign_key="company.id")
    certificate_number: str = Field(default="PENDIENTE")
    certificate_pdf_url: str | None = None
    notes: str | None = None


class EquipmentCalibrationResult(SQLModel, table=True):
    __tablename__ = "equipment_calibration_result"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)
    calibration_id: int = Field(foreign_key="equipment_calibration.id")
    point_label: str | None = None
    reference_value: float | None = None
    measured_value: float | None = None
    unit: str | None = None
    error_value: float | None = None
    tolerance_value: float | None = None
    volume_value: float | None = None
    systematic_error: float | None = None
    systematic_emp: float | None = None
    random_error: float | None = None
    random_emp: float | None = None
    uncertainty_value: float | None = None
    k_value: float | None = None
    is_ok: bool | None = None
    notes: str | None = None


class EquipmentCalibrationResultCreate(SQLModel):
    point_label: str | None = None
    reference_value: float | None = None
    measured_value: float | None = None
    unit: str | None = None
    error_value: float | None = None
    tolerance_value: float | None = None
    volume_value: float | None = None
    systematic_error: float | None = None
    systematic_emp: float | None = None
    random_error: float | None = None
    random_emp: float | None = None
    uncertainty_value: float | None = None
    k_value: float | None = None
    is_ok: bool | None = None
    notes: str | None = None


class EquipmentCalibrationCreate(SQLModel):
    calibrated_at: datetime | None = None
    calibration_company_id: int | None = None
    certificate_number: str
    notes: str | None = None
    results: list[EquipmentCalibrationResultCreate] = Field(default_factory=list)


class EquipmentCalibrationUpdate(SQLModel):
    calibrated_at: datetime | None = None
    calibration_company_id: int | None = None
    certificate_number: str | None = None
    certificate_pdf_url: str | None = None
    notes: str | None = None
    results: list[EquipmentCalibrationResultCreate] | None = None


class EquipmentCalibrationResultRead(SQLModel):
    id: int
    calibration_id: int
    point_label: str | None
    reference_value: float | None
    measured_value: float | None
    unit: str | None
    error_value: float | None
    tolerance_value: float | None
    volume_value: float | None
    systematic_error: float | None
    systematic_emp: float | None
    random_error: float | None
    random_emp: float | None
    uncertainty_value: float | None
    k_value: float | None
    is_ok: bool | None
    notes: str | None


class EquipmentCalibrationRead(SQLModel):
    id: int
    equipment_id: int
    calibrated_at: datetime
    created_by_user_id: int
    calibration_company_id: int | None
    certificate_number: str
    certificate_pdf_url: str | None
    notes: str | None
    results: list[EquipmentCalibrationResultRead] = Field(default_factory=list)


class EquipmentCalibrationListResponse(SQLModel):
    items: list[EquipmentCalibrationRead] = Field(default_factory=list)
    message: str | None = None
