"""rename equipment status available to stored

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-02-05 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
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
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'equipmentstatus'
                  AND e.enumlabel = 'available'
            ) THEN
                ALTER TYPE equipmentstatus RENAME VALUE 'available' TO 'stored';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'equipmentstatus'
                  AND e.enumlabel = 'stored'
            ) THEN
                ALTER TYPE equipmentstatus RENAME VALUE 'stored' TO 'available';
            END IF;
        END $$;
        """
    )
