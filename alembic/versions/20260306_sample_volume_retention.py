"""add volume and retention_days to sample

Revision ID: 20260306_sample_volume_retention
Revises: 20260305_add_volume_measure
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260306_sample_volume_retention"
down_revision = "20260305_add_volume_measure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sample", sa.Column("volume", sa.String(length=20), nullable=True))
    op.add_column("sample", sa.Column("retention_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("sample", "retention_days")
    op.drop_column("sample", "volume")
