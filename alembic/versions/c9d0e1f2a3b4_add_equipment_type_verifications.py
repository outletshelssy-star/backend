"""add equipment type verifications

Revision ID: c9d0e1f2a3b4
Revises: f3a4b5c6d7e8
Create Date: 2026-02-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c9d0e1f2a3b4"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipment_type_verification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("frequency_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_type.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "equipment_type_verification_item",
        sa.Column("verification_type_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "equipment_verification",
        sa.Column("verification_type_id", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_equipment_type_verification_item_verification_type_id",
        "equipment_type_verification_item",
        "equipment_type_verification",
        ["verification_type_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_equipment_verification_verification_type_id",
        "equipment_verification",
        "equipment_type_verification",
        ["verification_type_id"],
        ["id"],
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO equipment_type_verification
                (equipment_type_id, name, frequency_days, is_active, "order")
            SELECT id, 'Verificacion', verification_days, true, 0
            FROM equipment_type
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE equipment_type_verification_item AS item
            SET verification_type_id = v.id
            FROM equipment_type_verification v
            WHERE v.equipment_type_id = item.equipment_type_id
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE equipment_verification AS ev
            SET verification_type_id = v.id
            FROM equipment e
            JOIN equipment_type_verification v
                ON v.equipment_type_id = e.equipment_type_id
            WHERE ev.equipment_id = e.id
            """
        )
    )

    op.alter_column(
        "equipment_type_verification_item",
        "verification_type_id",
        nullable=False,
    )
    op.alter_column(
        "equipment_verification",
        "verification_type_id",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_equipment_verification_verification_type_id",
        "equipment_verification",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_equipment_type_verification_item_verification_type_id",
        "equipment_type_verification_item",
        type_="foreignkey",
    )
    op.drop_column("equipment_verification", "verification_type_id")
    op.drop_column("equipment_type_verification_item", "verification_type_id")
    op.drop_table("equipment_type_verification")
