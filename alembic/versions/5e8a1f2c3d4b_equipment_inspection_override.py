"""equipment inspection override

Revision ID: 5e8a1f2c3d4b
Revises: 6b7a2c1d9f0e
Create Date: 2026-02-05 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5e8a1f2c3d4b"
down_revision: Union[str, Sequence[str], None] = "6b7a2c1d9f0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "equipment",
        sa.Column("inspection_days_override", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("equipment", "inspection_days_override")
