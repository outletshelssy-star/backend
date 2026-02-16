"""add lab flags for terminals and equipment types

Revision ID: 20260216_term_lab_is_lab
Revises: 20260216_sample_water_volume
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_term_lab_is_lab"
down_revision = "20260216_sample_water_volume"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "equipment_type",
        sa.Column("is_lab", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "company_terminal",
        sa.Column("has_lab", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "company_terminal",
        sa.Column("lab_terminal_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_company_terminal_lab_terminal_id",
        "company_terminal",
        "company_terminal",
        ["lab_terminal_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_company_terminal_lab_terminal_id",
        "company_terminal",
        type_="foreignkey",
    )
    op.drop_column("company_terminal", "lab_terminal_id")
    op.drop_column("company_terminal", "has_lab")
    op.drop_column("equipment_type", "is_lab")
