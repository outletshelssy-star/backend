"""update company and equipment enums to english

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-02-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9c0d1e2f3a4b"
down_revision: Union[str, Sequence[str], None] = "8b9c0d1e2f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "UPDATE company SET company_type = 'client' WHERE company_type = 'cliente'"
    )
    op.execute(
        "UPDATE lab_equipment SET role = 'reference' WHERE role = 'patron'"
    )
    op.execute(
        "UPDATE lab_equipment SET role = 'working' WHERE role = 'trabajo'"
    )
    op.execute(
        "ALTER TYPE equipmentmeasuretype RENAME VALUE 'temperatura' TO 'temperature'"
    )
    op.execute(
        "ALTER TYPE equipmentmeasuretype RENAME VALUE 'presion' TO 'pressure'"
    )
    op.execute(
        "ALTER TYPE equipmentmeasuretype RENAME VALUE 'longitud' TO 'length'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TYPE equipmentmeasuretype RENAME VALUE 'temperature' TO 'temperatura'"
    )
    op.execute(
        "ALTER TYPE equipmentmeasuretype RENAME VALUE 'pressure' TO 'presion'"
    )
    op.execute(
        "ALTER TYPE equipmentmeasuretype RENAME VALUE 'length' TO 'longitud'"
    )
    op.execute(
        "UPDATE lab_equipment SET role = 'patron' WHERE role = 'reference'"
    )
    op.execute(
        "UPDATE lab_equipment SET role = 'trabajo' WHERE role = 'working'"
    )
    op.execute(
        "UPDATE company SET company_type = 'cliente' WHERE company_type = 'client'"
    )
