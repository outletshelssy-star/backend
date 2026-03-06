"""inspection item expected values

Revision ID: c1d2e3f4a5b6
Revises: 3a9e5c1b7d2f
Create Date: 2026-02-05 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "3a9e5c1b7d2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "equipment_type_inspection_item",
        sa.Column("expected_bool", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "equipment_type_inspection_item",
        sa.Column("expected_text_options", sa.JSON(), nullable=True),
    )
    op.add_column(
        "equipment_type_inspection_item",
        sa.Column("expected_number", sa.Float(), nullable=True),
    )
    op.add_column(
        "equipment_type_inspection_item",
        sa.Column("expected_number_min", sa.Float(), nullable=True),
    )
    op.add_column(
        "equipment_type_inspection_item",
        sa.Column("expected_number_max", sa.Float(), nullable=True),
    )
    op.add_column(
        "equipment_inspection_response",
        sa.Column("is_ok", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("equipment_inspection_response", "is_ok")
    op.drop_column("equipment_type_inspection_item", "expected_number_max")
    op.drop_column("equipment_type_inspection_item", "expected_number_min")
    op.drop_column("equipment_type_inspection_item", "expected_number")
    op.drop_column("equipment_type_inspection_item", "expected_text_options")
    op.drop_column("equipment_type_inspection_item", "expected_bool")
