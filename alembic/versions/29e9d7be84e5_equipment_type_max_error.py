"""equipment type max error

Revision ID: 29e9d7be84e5
Revises: 9ba80fe5d047
Create Date: 2026-02-05 11:10:23.561219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "29e9d7be84e5"
down_revision: Union[str, Sequence[str], None] = "9ba80fe5d047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "equipment_type_max_error",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_type_id", sa.Integer(), nullable=False),
        sa.Column(
            "measure",
            postgresql.ENUM(
                "temperature",
                "pressure",
                "length",
                name="equipmentmeasuretype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("max_error_value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_type.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("equipment_type_max_error")
