"""add water balance and sample weight to sample_analysis

Revision ID: 20260216_sample_water_balance
Revises: 20260216_sample_kf_equipment
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_sample_water_balance"
down_revision = "20260216_sample_kf_equipment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample_analysis",
        sa.Column("water_balance_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sample_analysis",
        sa.Column("water_sample_weight", sa.Float(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sample_analysis_water_balance_id_equipment",
        "sample_analysis",
        "equipment",
        ["water_balance_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sample_analysis_water_balance_id_equipment",
        "sample_analysis",
        type_="foreignkey",
    )
    op.drop_column("sample_analysis", "water_sample_weight")
    op.drop_column("sample_analysis", "water_balance_id")
