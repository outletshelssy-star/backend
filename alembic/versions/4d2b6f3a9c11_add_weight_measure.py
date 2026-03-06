"""add weight measure

Revision ID: 4d2b6f3a9c11
Revises: 7c1a9b3d2e10
Create Date: 2026-02-05 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d2b6f3a9c11"
down_revision: Union[str, Sequence[str], None] = "7c1a9b3d2e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'equipmentmeasuretype'
                  AND e.enumlabel = 'weight'
            ) THEN
                ALTER TYPE equipmentmeasuretype ADD VALUE 'weight';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres does not support removing enum values easily.
    # Leaving as-is on downgrade.
    return
