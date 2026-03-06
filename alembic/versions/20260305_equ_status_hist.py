"""equipment status history

Revision ID: 20260305_equ_status_hist
Revises: 20260304_terminal_product_name
Create Date: 2026-03-05 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260305_equ_status_hist"
down_revision = "20260304_terminal_product_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipment_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "stored",
                "in_use",
                "maintenance",
                "needs_review",
                "lost",
                "disposed",
                "unknown",
                name="equipmentstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO equipment_status_history (
                equipment_id,
                status,
                started_at,
                ended_at,
                changed_by_user_id
            )
            SELECT
                e.id,
                e.status,
                e.created_at,
                NULL,
                e.created_by_user_id
            FROM equipment e
            WHERE NOT EXISTS (
                SELECT 1
                FROM equipment_status_history esh
                WHERE esh.equipment_id = e.id
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_table("equipment_status_history")
