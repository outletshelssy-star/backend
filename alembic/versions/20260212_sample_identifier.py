"""add sample identifier

Revision ID: 20260212_sample_identifier
Revises: 20260212_samp_an_hist
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260212_sample_identifier"
down_revision = "20260212_samp_an_hist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sample", sa.Column("identifier", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("sample", "identifier")
