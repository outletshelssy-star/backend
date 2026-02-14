"""make sample analysis values nullable

Revision ID: 20260212_sample_nullable
Revises: 20260212_add_samples
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_sample_nullable"
down_revision = "20260212_add_samples"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "sample_analysis",
        "temp_obs_f",
        existing_type=sa.Float(),
        nullable=True,
    )
    op.alter_column(
        "sample_analysis",
        "lectura_api",
        existing_type=sa.Float(),
        nullable=True,
    )
    op.alter_column(
        "sample_analysis",
        "api_60f",
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "sample_analysis",
        "api_60f",
        existing_type=sa.Float(),
        nullable=False,
    )
    op.alter_column(
        "sample_analysis",
        "lectura_api",
        existing_type=sa.Float(),
        nullable=False,
    )
    op.alter_column(
        "sample_analysis",
        "temp_obs_f",
        existing_type=sa.Float(),
        nullable=False,
    )
