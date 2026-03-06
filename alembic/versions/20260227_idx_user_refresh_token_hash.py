"""add index on user.refresh_token_hash

Revision ID: 20260227_idx_user_refresh
Revises: 20260218_add_sample_thermo
Create Date: 2026-02-27 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260227_idx_user_refresh"
down_revision = "20260218_add_sample_thermo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_user_refresh_token_hash",
        "user",
        ["refresh_token_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_refresh_token_hash", table_name="user")
