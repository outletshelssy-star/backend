"""add water sample weight unit to sample_analysis

Revision ID: 20260216_sample_water_unit
Revises: 20260216_sample_water_balance
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_sample_water_unit"
down_revision = "20260216_sample_water_balance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample_analysis",
        sa.Column("water_sample_weight_unit", sa.String(length=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sample_analysis", "water_sample_weight_unit")
