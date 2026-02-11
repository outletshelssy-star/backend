"""equipment inspection items and responses

Revision ID: 8c4e1a7b2f6d
Revises: 5e8a1f2c3d4b
Create Date: 2026-02-05 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8c4e1a7b2f6d"
down_revision: Union[str, Sequence[str], None] = "5e8a1f2c3d4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'inspectionresponsetype'
            ) THEN
                CREATE TYPE inspectionresponsetype AS ENUM (
                    'boolean',
                    'text',
                    'number'
                );
            END IF;
        END $$;
        """
    )

    op.create_table(
        "equipment_type_inspection_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_type_id", sa.Integer(), nullable=False),
        sa.Column("item", sa.String(), nullable=False),
        sa.Column(
            "response_type",
            postgresql.ENUM(
                "boolean",
                "text",
                "number",
                name="inspectionresponsetype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_type.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "equipment_inspection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("inspected_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "equipment_inspection_response",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("inspection_id", sa.Integer(), nullable=False),
        sa.Column("inspection_item_id", sa.Integer(), nullable=False),
        sa.Column(
            "response_type",
            postgresql.ENUM(
                "boolean",
                "text",
                "number",
                name="inspectionresponsetype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("value_text", sa.String(), nullable=True),
        sa.Column("value_number", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["inspection_id"], ["equipment_inspection.id"]),
        sa.ForeignKeyConstraint(
            ["inspection_item_id"],
            ["equipment_type_inspection_item.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("equipment_inspection_response")
    op.drop_table("equipment_inspection")
    op.drop_table("equipment_type_inspection_item")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'inspectionresponsetype'
            ) THEN
                DROP TYPE inspectionresponsetype;
            END IF;
        END $$;
        """
    )
