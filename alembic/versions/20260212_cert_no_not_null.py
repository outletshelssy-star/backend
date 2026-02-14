"""make calibration certificate number not null

Revision ID: 20260212_cert_no_not_null
Revises: 20260212_add_cal_cert_no
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_cert_no_not_null"
down_revision = "20260212_add_cal_cert_no"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE equipment_calibration SET certificate_number='PENDIENTE' "
        "WHERE certificate_number IS NULL OR certificate_number = ''"
    )
    op.alter_column(
        "equipment_calibration",
        "certificate_number",
        existing_type=sa.String(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "equipment_calibration",
        "certificate_number",
        existing_type=sa.String(),
        nullable=True,
    )
