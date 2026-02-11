"""drop verification_days from equipment_type

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-02-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("equipment_type", "verification_days")


def downgrade() -> None:
    op.add_column(
        "equipment_type",
        sa.Column("verification_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("equipment_type", "verification_days", server_default=None)
