"""increase emp_value precision

Revision ID: 20260213_emp_value_scale
Revises: 20260213_equ_emp_f
Create Date: 2026-02-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260213_emp_value_scale"
down_revision: Union[str, Sequence[str], None] = "20260213_equ_emp_f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "equipment",
        "emp_value",
        existing_type=sa.Numeric(12, 3),
        type_=sa.Numeric(12, 6),
    )


def downgrade() -> None:
    op.alter_column(
        "equipment",
        "emp_value",
        existing_type=sa.Numeric(12, 6),
        type_=sa.Numeric(12, 3),
    )
