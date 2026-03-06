"""add calibration certificate number

Revision ID: 20260212_add_cal_cert_no
Revises: 20260212_merge_heads
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_add_cal_cert_no"
down_revision = "20260212_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "equipment_calibration",
        sa.Column("certificate_number", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("equipment_calibration", "certificate_number")
