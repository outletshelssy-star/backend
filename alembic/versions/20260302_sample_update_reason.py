"""add last_update_reason to sample

Revision ID: 20260302_sample_update_reason
Revises: 20260227_idx_user_refresh
Create Date: 2026-03-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260302_sample_update_reason"
down_revision = "20260227_idx_user_refresh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sample", sa.Column("last_update_reason", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("sample", "last_update_reason")
