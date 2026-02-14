"""add percent_pv to equipmentmeasuretype

Revision ID: 20260213_add_percent_pv_measure
Revises: 20260213_emp_value_scale
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260213_add_percent_pv_measure'
down_revision = '20260213_emp_value_scale'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE equipmentmeasuretype ADD VALUE IF NOT EXISTS 'percent_pv'")


def downgrade() -> None:
    # Removing enum values in Postgres is non-trivial; keep as no-op.
    pass
