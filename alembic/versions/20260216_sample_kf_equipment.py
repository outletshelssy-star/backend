"""add kf_equipment_id to sample_analysis

Revision ID: 20260216_sample_kf_equipment
Revises: 20260216_sample_kf_factor
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_sample_kf_equipment"
down_revision = "20260216_sample_kf_factor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample_analysis",
        sa.Column("kf_equipment_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sample_analysis_kf_equipment_id_equipment",
        "sample_analysis",
        "equipment",
        ["kf_equipment_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_sample_analysis_kf_equipment_id_equipment",
        "sample_analysis",
        type_="foreignkey",
    )
    op.drop_column("sample_analysis", "kf_equipment_id")
