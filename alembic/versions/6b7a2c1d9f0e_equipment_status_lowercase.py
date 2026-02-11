"""equipment status lowercase

Revision ID: 6b7a2c1d9f0e
Revises: 4d2b6f3a9c11
Create Date: 2026-02-05 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b7a2c1d9f0e"
down_revision: Union[str, Sequence[str], None] = "4d2b6f3a9c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'equipmentstatus') THEN
                CREATE TYPE equipmentstatus_new AS ENUM (
                    'available',
                    'in_use',
                    'maintenance',
                    'lost',
                    'disposed',
                    'unknown'
                );

                ALTER TABLE equipment
                ALTER COLUMN status
                TYPE equipmentstatus_new
                USING LOWER(status::text)::equipmentstatus_new;

                DROP TYPE equipmentstatus;
                ALTER TYPE equipmentstatus_new RENAME TO equipmentstatus;
            ELSE
                CREATE TYPE equipmentstatus AS ENUM (
                    'available',
                    'in_use',
                    'maintenance',
                    'lost',
                    'disposed',
                    'unknown'
                );
                ALTER TABLE equipment
                ALTER COLUMN status
                TYPE equipmentstatus
                USING status::text::equipmentstatus;
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
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'equipmentstatus') THEN
                CREATE TYPE equipmentstatus_old AS ENUM (
                    'AVAILABLE',
                    'IN_USE',
                    'MAINTENANCE',
                    'LOST',
                    'DISPOSED',
                    'UNKNOWN'
                );

                UPDATE equipment
                SET status = UPPER(status)
                WHERE status IS NOT NULL;

                ALTER TABLE equipment
                ALTER COLUMN status
                TYPE equipmentstatus_old
                USING status::text::equipmentstatus_old;

                DROP TYPE equipmentstatus;
                ALTER TYPE equipmentstatus_old RENAME TO equipmentstatus;
            END IF;
        END $$;
        """
    )
