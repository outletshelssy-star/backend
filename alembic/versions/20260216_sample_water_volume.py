"""add water volume to sample_analysis

Revision ID: 20260216_sample_water_volume
Revises: 20260216_sample_water_unit
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_sample_water_volume"
down_revision = "20260216_sample_water_unit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample_analysis",
        sa.Column("water_volume_consumed", sa.Float(), nullable=True),
    )
    op.add_column(
        "sample_analysis",
        sa.Column("water_volume_unit", sa.String(length=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sample_analysis", "water_volume_unit")
    op.drop_column("sample_analysis", "water_volume_consumed")
