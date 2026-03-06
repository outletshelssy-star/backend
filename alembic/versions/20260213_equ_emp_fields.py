"""add weight class and emp fields to equipment

Revision ID: 20260213_equ_emp_f
Revises: 20260213_back_term_hist
Create Date: 2026-02-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260213_equ_emp_f"
down_revision: Union[str, Sequence[str], None] = "20260213_back_term_hist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "equipment",
        sa.Column("weight_class", sa.String(length=5), nullable=True),
    )
    op.add_column(
        "equipment",
        sa.Column("nominal_mass_value", sa.Numeric(12, 3), nullable=True),
    )
    op.add_column(
        "equipment",
        sa.Column("nominal_mass_unit", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "equipment",
        sa.Column("emp_value", sa.Numeric(12, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("equipment", "emp_value")
    op.drop_column("equipment", "nominal_mass_unit")
    op.drop_column("equipment", "nominal_mass_value")
    op.drop_column("equipment", "weight_class")
