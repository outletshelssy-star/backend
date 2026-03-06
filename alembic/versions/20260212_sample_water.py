"""add water value to sample analysis

Revision ID: 20260212_sample_water
Revises: 20260212_sample_details
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_sample_water"
down_revision = "20260212_sample_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample_analysis",
        sa.Column("water_value", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sample_analysis", "water_value")
