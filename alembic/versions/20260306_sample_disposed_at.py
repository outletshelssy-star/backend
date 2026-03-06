"""add disposed_at to sample

Revision ID: 20260306_sample_disposed_at
Revises: 20260306_sample_volume_retention
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260306_sample_disposed_at"
down_revision = "20260306_sample_volume_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sample", sa.Column("disposed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sample", "disposed_at")
