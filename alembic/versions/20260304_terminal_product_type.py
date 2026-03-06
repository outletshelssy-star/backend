"""add terminal_product_type table

Revision ID: 20260304_terminal_product_type
Revises: 20260302_sample_update_reason
Create Date: 2026-03-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260304_terminal_product_type"
down_revision = "20260302_sample_update_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "terminal_product_type",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("terminal_id", sa.Integer(), nullable=False),
        sa.Column("product_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["terminal_id"], ["company_terminal.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("terminal_id", "product_type", name="uq_terminal_product_type"),
    )
    op.create_index("ix_terminal_product_type_terminal_id", "terminal_product_type", ["terminal_id"])


def downgrade() -> None:
    op.drop_index("ix_terminal_product_type_terminal_id", table_name="terminal_product_type")
    op.drop_table("terminal_product_type")
