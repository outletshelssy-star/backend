from typing import Sequence, Union

from alembic import op


revision: str = "20260212_add_user_type_visitor"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'visitor'")


def downgrade() -> None:
    # PostgreSQL enums do not support dropping values safely.
    pass
