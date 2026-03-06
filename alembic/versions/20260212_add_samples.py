"""add samples and analysis tables

Revision ID: 20260212_add_samples
Revises: 20260212_cert_no_not_null
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_add_samples"
down_revision = "20260212_cert_no_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "company_terminal",
        sa.Column("next_sample_sequence", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("company_terminal", "next_sample_sequence", server_default=None)

    op.create_table(
        "sample",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("terminal_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["terminal_id"], ["company_terminal.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sample_code", "sample", ["code"])
    op.create_index("ix_sample_sequence", "sample", ["sequence"])

    op.create_table(
        "sample_analysis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.Integer(), nullable=False),
        sa.Column("analysis_type", sa.String(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("temp_obs_f", sa.Float(), nullable=False),
        sa.Column("lectura_api", sa.Float(), nullable=False),
        sa.Column("api_60f", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["sample.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sample_analysis")
    op.drop_index("ix_sample_sequence", table_name="sample")
    op.drop_index("ix_sample_code", table_name="sample")
    op.drop_table("sample")
    op.drop_column("company_terminal", "next_sample_sequence")
