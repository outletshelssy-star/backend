"""add equipment verification tables

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
Create Date: 2026-02-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f3a4b5c6d7e8"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipment_type_verification_item",
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
        sa.Column("expected_bool", sa.Boolean(), nullable=True),
        sa.Column("expected_text_options", sa.JSON(), nullable=True),
        sa.Column("expected_number", sa.Float(), nullable=True),
        sa.Column("expected_number_min", sa.Float(), nullable=True),
        sa.Column("expected_number_max", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_type.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "equipment_verification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("is_ok", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "equipment_verification_response",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("verification_id", sa.Integer(), nullable=False),
        sa.Column("verification_item_id", sa.Integer(), nullable=False),
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
        sa.Column("is_ok", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["verification_id"],
            ["equipment_verification.id"],
        ),
        sa.ForeignKeyConstraint(
            ["verification_item_id"],
            ["equipment_type_verification_item.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("equipment_verification_response")
    op.drop_table("equipment_verification")
    op.drop_table("equipment_type_verification_item")
