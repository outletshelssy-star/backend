"""add api measure

Revision ID: 20260212_add_api_measure
Revises: f7a8b9c0d1e2
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260212_add_api_measure"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
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
                  AND e.enumlabel = 'api'
            ) THEN
                ALTER TYPE equipmentmeasuretype ADD VALUE 'api';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres does not support removing enum values easily.
    return
