"""allow alphanumeric terminal codes

Revision ID: 20260216_term_code_alnum
Revises: 20260216_add_rel_humidity
Create Date: 2026-02-16
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260216_term_code_alnum"
down_revision = "20260216_add_rel_humidity"
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
          AND terminal_code !~ '^[A-Z0-9]{3,4}$'
        """
    )
    op.drop_constraint("ck_company_terminal_code_format", "company_terminal", type_="check")
    op.create_check_constraint(
        "ck_company_terminal_code_format",
        "company_terminal",
        "terminal_code IS NULL OR terminal_code ~ '^[A-Z0-9]{3,4}$'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_company_terminal_code_format", "company_terminal", type_="check")
    op.create_check_constraint(
        "ck_company_terminal_code_format",
        "company_terminal",
        "terminal_code IS NULL OR terminal_code ~ '^[A-Z]{3,4}$'",
    )
