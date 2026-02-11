"""remove terminal_id from equipment_type

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-02-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'equipment_type'
                  AND constraint_name = 'equipment_type_terminal_id_fkey'
            ) THEN
                ALTER TABLE equipment_type
                DROP CONSTRAINT equipment_type_terminal_id_fkey;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'equipment_type'
                  AND column_name = 'terminal_id'
            ) THEN
                ALTER TABLE equipment_type
                DROP COLUMN terminal_id;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "equipment_type",
        sa.Column("terminal_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "equipment_type_terminal_id_fkey",
        "equipment_type",
        "company_terminal",
        ["terminal_id"],
        ["id"],
    )
