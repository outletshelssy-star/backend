"""merge heads

Revision ID: 20260212_merge_heads
Revises: 20260212_add_api_measure, 20260212_add_user_type_visitor
Create Date: 2026-02-12 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260212_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "20260212_add_api_measure",
    "20260212_add_user_type_visitor",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
