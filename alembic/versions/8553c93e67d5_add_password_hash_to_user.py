"""add password hash to user

Revision ID: 8553c93e67d5
Revises: 12589266de81
Create Date: 2026-01-23 15:20:08.513548
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8553c93e67d5"
down_revision: Union[str, Sequence[str], None] = "12589266de81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1️⃣ Agregar la columna como nullable
    op.add_column(
        "user",
        sa.Column("password_hash", sa.String(), nullable=True),
    )

    # 2️⃣ Setear un valor temporal para registros existentes
    op.execute(
        "UPDATE \"user\" SET password_hash = 'TEMP_CHANGE_ME'"
    )

    # 3️⃣ Hacer la columna NOT NULL
    op.alter_column(
        "user",
        "password_hash",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "password_hash")

