"""remove company_id from equipment

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-02-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("equipment_company_id_fkey", "equipment", type_="foreignkey")
    op.drop_column("equipment", "company_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "equipment",
        sa.Column("company_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "equipment_company_id_fkey",
        "equipment",
        "company",
        ["company_id"],
        ["id"],
    )
