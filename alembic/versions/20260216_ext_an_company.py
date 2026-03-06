"""add company to external analysis record

Revision ID: 20260216_ext_an_company
Revises: 20260213_ext_an_rec
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_ext_an_company"
down_revision = "20260213_ext_an_rec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "external_analysis_record",
        sa.Column("analysis_company_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_external_analysis_record_analysis_company_id_company",
        "external_analysis_record",
        "company",
        ["analysis_company_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_external_analysis_record_analysis_company_id_company",
        "external_analysis_record",
        type_="foreignkey",
    )
    op.drop_column("external_analysis_record", "analysis_company_id")
