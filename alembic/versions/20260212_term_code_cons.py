"""terminal code constraints

Revision ID: 20260212_term_code_cons
Revises: 20260212_drop_terminal_prefix
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260212_term_code_cons"
down_revision = "20260212_drop_terminal_prefix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE company_terminal
        SET terminal_code = UPPER(TRIM(terminal_code))
        WHERE terminal_code IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE company_terminal
        SET terminal_code = NULL
        WHERE terminal_code IS NOT NULL
          AND terminal_code !~ '^[A-Z]{3,4}$'
        """
    )
    op.alter_column(
        "company_terminal",
        "terminal_code",
        existing_type=sa.String(length=32),
        type_=sa.String(length=4),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "ck_company_terminal_code_format",
        "company_terminal",
        "terminal_code IS NULL OR terminal_code ~ '^[A-Z]{3,4}$'",
    )
    op.create_index(
        "uq_company_terminal_terminal_code",
        "company_terminal",
        ["terminal_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_company_terminal_terminal_code", table_name="company_terminal")
    op.drop_constraint("ck_company_terminal_code_format", "company_terminal", type_="check")
    op.alter_column(
        "company_terminal",
        "terminal_code",
        existing_type=sa.String(length=4),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
