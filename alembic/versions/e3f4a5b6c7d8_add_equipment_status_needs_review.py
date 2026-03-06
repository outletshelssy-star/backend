"""add equipment status needs review

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-02-05 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'equipmentstatus') THEN
                ALTER TYPE equipmentstatus ADD VALUE IF NOT EXISTS 'needs_review';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Removing enum values in Postgres requires recreating the type.
    pass
