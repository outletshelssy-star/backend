"""add relative_humidity to equipmentmeasuretype enum

Revision ID: 20260216_add_rel_humidity
Revises: 20260216_term_lab_is_lab
Create Date: 2026-02-16
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260216_add_rel_humidity"
down_revision = "20260216_term_lab_is_lab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE equipmentmeasuretype ADD VALUE IF NOT EXISTS 'relative_humidity'"
    )


def downgrade() -> None:
    # Postgres does not support removing enum values safely.
    pass
