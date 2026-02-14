"""add external analysis report fields

Revision ID: 20260213_ext_an_rec
Revises: 20260213_ext_analysis_defaults
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260213_ext_an_rec'
down_revision = '20260213_ext_analysis_defaults'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'external_analysis_record',
        sa.Column('report_number', sa.String(), nullable=True),
    )
    op.add_column(
        'external_analysis_record',
        sa.Column('report_pdf_url', sa.String(), nullable=True),
    )
    op.add_column(
        'external_analysis_record',
        sa.Column('result_value', sa.Float(), nullable=True),
    )
    op.add_column(
        'external_analysis_record',
        sa.Column('result_unit', sa.String(), nullable=True),
    )
    op.add_column(
        'external_analysis_record',
        sa.Column('result_uncertainty', sa.Float(), nullable=True),
    )
    op.add_column(
        'external_analysis_record',
        sa.Column('method', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('external_analysis_record', 'method')
    op.drop_column('external_analysis_record', 'result_uncertainty')
    op.drop_column('external_analysis_record', 'result_unit')
    op.drop_column('external_analysis_record', 'result_value')
    op.drop_column('external_analysis_record', 'report_pdf_url')
    op.drop_column('external_analysis_record', 'report_number')
