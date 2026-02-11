"""update company type aliado to partner

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-02-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4d5e6f7a8b9c"
down_revision: Union[str, Sequence[str], None] = "3c4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE company SET company_type = 'partner' WHERE company_type = 'aliado'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE company SET company_type = 'aliado' WHERE company_type = 'partner'")
