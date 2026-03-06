"""add external analyses

Revision ID: 20260213_ext_analysis
Revises: 20260213_kf_calib_fields
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260213_ext_analysis'
down_revision = '20260213_kf_calib_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'external_analysis_type',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('default_frequency_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id']),
        sa.UniqueConstraint('name', name='uq_external_analysis_type_name'),
    )
    op.create_index('ix_external_analysis_type_name', 'external_analysis_type', ['name'])

    op.create_table(
        'external_analysis_terminal',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('terminal_id', sa.Integer(), nullable=False),
        sa.Column('analysis_type_id', sa.Integer(), nullable=False),
        sa.Column('frequency_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['terminal_id'], ['company_terminal.id']),
        sa.ForeignKeyConstraint(['analysis_type_id'], ['external_analysis_type.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id']),
        sa.UniqueConstraint('terminal_id', 'analysis_type_id', name='uq_external_analysis_terminal'),
    )
    op.create_index('ix_external_analysis_terminal_terminal_id', 'external_analysis_terminal', ['terminal_id'])

    op.create_table(
        'external_analysis_record',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('terminal_id', sa.Integer(), nullable=False),
        sa.Column('analysis_type_id', sa.Integer(), nullable=False),
        sa.Column('performed_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['terminal_id'], ['company_terminal.id']),
        sa.ForeignKeyConstraint(['analysis_type_id'], ['external_analysis_type.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id']),
    )
    op.create_index('ix_external_analysis_record_terminal_id', 'external_analysis_record', ['terminal_id'])
    op.create_index('ix_external_analysis_record_type_id', 'external_analysis_record', ['analysis_type_id'])


def downgrade() -> None:
    op.drop_index('ix_external_analysis_record_type_id', table_name='external_analysis_record')
    op.drop_index('ix_external_analysis_record_terminal_id', table_name='external_analysis_record')
    op.drop_table('external_analysis_record')
    op.drop_index('ix_external_analysis_terminal_terminal_id', table_name='external_analysis_terminal')
    op.drop_table('external_analysis_terminal')
    op.drop_index('ix_external_analysis_type_name', table_name='external_analysis_type')
    op.drop_table('external_analysis_type')
