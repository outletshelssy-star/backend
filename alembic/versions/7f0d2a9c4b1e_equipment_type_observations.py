"""equipment type observations

Revision ID: 7f0d2a9c4b1e
Revises: 8c4e1a7b2f6d
Create Date: 2026-02-05 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7f0d2a9c4b1e"
down_revision: Union[str, Sequence[str], None] = "8c4e1a7b2f6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "equipment_type",
        sa.Column("observations", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("equipment_type", "observations")
