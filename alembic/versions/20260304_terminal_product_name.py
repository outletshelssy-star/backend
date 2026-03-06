"""add name to terminal_product_type

Revision ID: 20260304_terminal_product_name
Revises: 20260304_terminal_product_type
Create Date: 2026-03-04 01:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "20260304_terminal_product_name"
down_revision = "20260304_terminal_product_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("terminal_product_type") as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=120), nullable=True))

    op.execute(
        sa.text(
            "UPDATE terminal_product_type "
            "SET name = CASE product_type "
            "WHEN 'crudo' THEN 'Crudo' "
            "WHEN 'gasolina' THEN 'Gasolina' "
            "WHEN 'diesel' THEN 'Diesel' "
            "ELSE product_type END "
            "WHERE name IS NULL"
        )
    )

    with op.batch_alter_table("terminal_product_type") as batch_op:
        batch_op.alter_column("name", existing_type=sa.String(length=120), nullable=False)
        batch_op.drop_constraint("uq_terminal_product_type", type_="unique")
        batch_op.create_unique_constraint(
            "uq_terminal_product_name",
            ["terminal_id", "name"],
        )


def downgrade() -> None:
    with op.batch_alter_table("terminal_product_type") as batch_op:
        batch_op.drop_constraint("uq_terminal_product_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_terminal_product_type",
            ["terminal_id", "product_type"],
        )
        batch_op.drop_column("name")
