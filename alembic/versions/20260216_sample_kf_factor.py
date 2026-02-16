"""add kf_factor_avg to sample_analysis

Revision ID: 20260216_sample_kf_factor
Revises: 20260216_company_active
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_sample_kf_factor"
down_revision = "20260216_company_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample_analysis",
        sa.Column("kf_factor_avg", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sample_analysis", "kf_factor_avg")
