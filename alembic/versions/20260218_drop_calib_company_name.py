"""drop calibration company name from equipment calibration

Revision ID: 20260218_drop_calib_company_name
Revises: 20260216_term_code_alnum
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260218_drop_calib_company_name"
down_revision = "20260216_term_code_alnum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("equipment_calibration", "calibration_company_name")


def downgrade() -> None:
    op.add_column(
        "equipment_calibration",
        sa.Column("calibration_company_name", sa.String(), nullable=True),
    )
