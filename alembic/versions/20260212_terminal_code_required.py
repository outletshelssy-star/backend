"""terminal code required

Revision ID: 20260212_term_code_req
Revises: 20260212_term_code_cons
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260212_term_code_req"
down_revision = "20260212_term_code_cons"
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
        SET terminal_code = LEFT(REGEXP_REPLACE(UPPER(name), '[^A-Z]', '', 'g'), 4)
        WHERE terminal_code IS NULL
          AND LENGTH(REGEXP_REPLACE(UPPER(name), '[^A-Z]', '', 'g')) BETWEEN 3 AND 4
        """
    )
    op.execute(
        """
        WITH to_update AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn
            FROM company_terminal
            WHERE terminal_code IS NULL
        ),
        letters AS (
            SELECT ARRAY['A','B','C','D','E','F','G','H','I','J','K','L','M',
                         'N','O','P','Q','R','S','T','U','V','W','X','Y','Z'] AS arr
        )
        UPDATE company_terminal ct
        SET terminal_code = CASE
            WHEN tu.rn <= 26 THEN 'TR' || letters.arr[tu.rn]
            ELSE 'T' ||
                 letters.arr[((tu.rn - 1) / 26)::int + 1] ||
                 letters.arr[((tu.rn - 1) % 26)::int + 1]
        END
        FROM to_update tu, letters
        WHERE ct.id = tu.id
        """
    )
    op.execute(
        """
        UPDATE company_terminal
        SET terminal_code = SUBSTRING(terminal_code FROM 1 FOR 4)
        WHERE terminal_code IS NOT NULL AND LENGTH(terminal_code) > 4
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
        existing_type=sa.String(length=4),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "company_terminal",
        "terminal_code",
        existing_type=sa.String(length=4),
        nullable=True,
    )
