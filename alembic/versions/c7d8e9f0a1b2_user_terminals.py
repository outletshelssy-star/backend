"""add user terminals relation

Revision ID: c7d8e9f0a1b2
Revises: b2c3d4e5f6a7
Create Date: 2026-02-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_terminal",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("terminal_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["terminal_id"], ["company_terminal.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.UniqueConstraint("user_id", "terminal_id", name="uq_user_terminal"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("user_terminal")
