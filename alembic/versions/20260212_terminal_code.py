"""add terminal code

Revision ID: 20260212_terminal_code
Revises: 20260212_terminal_prefix
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260212_terminal_code"
down_revision = "20260212_terminal_prefix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "company_terminal",
        sa.Column("terminal_code", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("company_terminal", "terminal_code")
