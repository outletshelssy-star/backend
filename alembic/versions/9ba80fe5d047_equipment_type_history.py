"""equipment type history

Revision ID: 9ba80fe5d047
Revises: e50532f7248f
Create Date: 2026-02-05 10:54:33.382865

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9ba80fe5d047"
down_revision: Union[str, Sequence[str], None] = "e50532f7248f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "equipment_type_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("equipment_type_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_type.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("equipment_type_history")
