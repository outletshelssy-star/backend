"""equipment measure specs and status

Revision ID: 3f2a1c9b7d8e
Revises: 29e9d7be84e5
Create Date: 2026-02-05 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3f2a1c9b7d8e"
down_revision: Union[str, Sequence[str], None] = "29e9d7be84e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'equipmentstatus'
            ) THEN
                CREATE TYPE equipmentstatus AS ENUM (
                    'AVAILABLE',
                    'IN_USE',
                    'MAINTENANCE',
                    'LOST',
                    'DISPOSED',
                    'UNKNOWN'
                );
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        UPDATE equipment
        SET status = 'UNKNOWN'
        WHERE status IS NULL
           OR status NOT IN (
                'AVAILABLE',
                'IN_USE',
                'MAINTENANCE',
                'LOST',
                'DISPOSED',
                'UNKNOWN'
           );
        """
    )
    op.alter_column(
        "equipment",
        "status",
        type_=postgresql.ENUM(
            "AVAILABLE",
            "IN_USE",
            "MAINTENANCE",
            "LOST",
            "DISPOSED",
            "UNKNOWN",
            name="equipmentstatus",
            create_type=False,
        ),
        postgresql_using="status::equipmentstatus",
        existing_type=sa.VARCHAR(),
        existing_nullable=False,
    )
    op.create_table(
        "equipment_measure_spec",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column(
            "measure",
            postgresql.ENUM(
                "temperature",
                "pressure",
                "length",
                name="equipmentmeasuretype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("resolution", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("equipment_measure_spec")
    op.alter_column(
        "equipment",
        "status",
        type_=sa.VARCHAR(),
        existing_type=postgresql.ENUM(
            "AVAILABLE",
            "IN_USE",
            "MAINTENANCE",
            "LOST",
            "DISPOSED",
            "UNKNOWN",
            name="equipmentstatus",
        ),
        existing_nullable=False,
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'equipmentstatus'
            ) THEN
                DROP TYPE equipmentstatus;
            END IF;
        END $$;
        """
    )
