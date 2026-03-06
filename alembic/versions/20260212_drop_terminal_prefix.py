"""drop terminal sample code prefix

Revision ID: 20260212_drop_terminal_prefix
Revises: 20260212_terminal_code
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260212_drop_terminal_prefix"
down_revision = "20260212_terminal_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE company_terminal
        SET terminal_code = sample_code_prefix
        WHERE terminal_code IS NULL AND sample_code_prefix IS NOT NULL
        """
    )
    op.drop_column("company_terminal", "sample_code_prefix")


def downgrade() -> None:
    op.add_column(
        "company_terminal",
        sa.Column("sample_code_prefix", sa.String(length=12), nullable=True),
    )
