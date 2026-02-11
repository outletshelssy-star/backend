"""remove company fields from equipment_type

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
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
                  AND constraint_name = 'equipment_type_company_id_fkey'
            ) THEN
                ALTER TABLE equipment_type
                DROP CONSTRAINT equipment_type_company_id_fkey;
            END IF;
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = 'equipment_type'
                  AND constraint_name = 'equipment_type_owner_company_id_fkey'
            ) THEN
                ALTER TABLE equipment_type
                DROP CONSTRAINT equipment_type_owner_company_id_fkey;
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
                  AND column_name = 'company_id'
            ) THEN
                ALTER TABLE equipment_type
                DROP COLUMN company_id;
            END IF;
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'equipment_type'
                  AND column_name = 'owner_company_id'
            ) THEN
                ALTER TABLE equipment_type
                DROP COLUMN owner_company_id;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "equipment_type",
        sa.Column("company_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "equipment_type",
        sa.Column("owner_company_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "equipment_type_company_id_fkey",
        "equipment_type",
        "company",
        ["company_id"],
        ["id"],
    )
    op.create_foreign_key(
        "equipment_type_owner_company_id_fkey",
        "equipment_type",
        "company",
        ["owner_company_id"],
        ["id"],
    )
