from datetime import UTC, datetime

from sqlmodel import Field


class AuditMixin:
    """Mixin para campos de auditoría."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        description="Fecha y hora de creación (UTC).",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
        description="Fecha y hora de última actualización (UTC).",
    )

    @staticmethod
    def update_timestamp(mapper, connection, target) -> None:
        target.updated_at = datetime.now(UTC)
