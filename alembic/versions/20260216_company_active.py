"""add is_active to company

Revision ID: 20260216_company_active
Revises: 20260216_ext_an_company
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_company_active"
down_revision = "20260216_ext_an_company"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "company",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("company", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("company", "is_active")
