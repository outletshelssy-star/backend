"""add disposed_by_user_id to sample

Revision ID: 20260306_sample_disposed_by
Revises: 20260306_sample_disposed_at
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260306_sample_disposed_by"
down_revision = "20260306_sample_disposed_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample",
        sa.Column("disposed_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sample", "disposed_by_user_id")
