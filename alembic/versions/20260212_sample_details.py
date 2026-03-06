"""add sample details and analysis equipment

Revision ID: 20260212_sample_details
Revises: 20260212_sample_nullable
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_sample_details"
down_revision = "20260212_sample_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sample",
        sa.Column("product_name", sa.String(), nullable=False, server_default="Crudo"),
    )
    op.add_column(
        "sample",
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sample",
        sa.Column("lab_humidity", sa.Float(), nullable=True),
    )
    op.add_column(
        "sample",
        sa.Column("lab_temperature", sa.Float(), nullable=True),
    )
    op.alter_column("sample", "product_name", server_default=None)

    op.add_column(
        "sample_analysis",
        sa.Column("hydrometer_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sample_analysis",
        sa.Column("thermometer_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sample_analysis_hydrometer",
        "sample_analysis",
        "equipment",
        ["hydrometer_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_sample_analysis_thermometer",
        "sample_analysis",
        "equipment",
        ["thermometer_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_sample_analysis_thermometer", "sample_analysis", type_="foreignkey")
    op.drop_constraint("fk_sample_analysis_hydrometer", "sample_analysis", type_="foreignkey")
    op.drop_column("sample_analysis", "thermometer_id")
    op.drop_column("sample_analysis", "hydrometer_id")
    op.drop_column("sample", "lab_temperature")
    op.drop_column("sample", "lab_humidity")
    op.drop_column("sample", "analyzed_at")
    op.drop_column("sample", "product_name")
