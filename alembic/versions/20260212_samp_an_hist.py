"""add sample analysis history

Revision ID: 20260212_samp_an_hist
Revises: 20260212_sample_water
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260212_samp_an_hist"
down_revision = "20260212_sample_water"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sample_analysis_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sample_analysis_id", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.Integer(), nullable=False),
        sa.Column("analysis_type", sa.String(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("product_name_before", sa.String(), nullable=True),
        sa.Column("product_name_after", sa.String(), nullable=True),
        sa.Column("temp_obs_f_before", sa.Float(), nullable=True),
        sa.Column("temp_obs_f_after", sa.Float(), nullable=True),
        sa.Column("lectura_api_before", sa.Float(), nullable=True),
        sa.Column("lectura_api_after", sa.Float(), nullable=True),
        sa.Column("api_60f_before", sa.Float(), nullable=True),
        sa.Column("api_60f_after", sa.Float(), nullable=True),
        sa.Column("hydrometer_id_before", sa.Integer(), nullable=True),
        sa.Column("hydrometer_id_after", sa.Integer(), nullable=True),
        sa.Column("thermometer_id_before", sa.Integer(), nullable=True),
        sa.Column("thermometer_id_after", sa.Integer(), nullable=True),
        sa.Column("water_value_before", sa.Float(), nullable=True),
        sa.Column("water_value_after", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(
            ["sample_analysis_id"],
            ["sample_analysis.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["sample_id"], ["sample.id"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["hydrometer_id_before"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["hydrometer_id_after"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["thermometer_id_before"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["thermometer_id_after"], ["equipment.id"]),
    )
    op.create_index(
        "ix_sample_analysis_history_sample_analysis_id",
        "sample_analysis_history",
        ["sample_analysis_id"],
    )
    op.create_index(
        "ix_sample_analysis_history_sample_id",
        "sample_analysis_history",
        ["sample_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_sample_analysis_history_sample_id", table_name="sample_analysis_history")
    op.drop_index("ix_sample_analysis_history_sample_analysis_id", table_name="sample_analysis_history")
    op.drop_table("sample_analysis_history")
