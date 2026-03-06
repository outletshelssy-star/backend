"""add thermohygrometer to sample

Revision ID: 20260218_add_sample_thermo
Revises: 20260218_drop_calib_company_name
Create Date: 2026-02-18 16:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260218_add_sample_thermo"
down_revision = "20260218_drop_calib_company_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample",
        sa.Column(
            "thermohygrometer_id",
            sa.Integer(),
            sa.ForeignKey("equipment.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("sample", "thermohygrometer_id")
