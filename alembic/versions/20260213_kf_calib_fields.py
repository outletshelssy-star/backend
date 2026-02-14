"""add karl fischer calibration result fields

Revision ID: 20260213_kf_calib_fields
Revises: 20260213_add_percent_pv_measure
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260213_kf_calib_fields'
down_revision = '20260213_add_percent_pv_measure'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('equipment_calibration_result', sa.Column('volume_value', sa.Float(), nullable=True))
    op.add_column('equipment_calibration_result', sa.Column('systematic_error', sa.Float(), nullable=True))
    op.add_column('equipment_calibration_result', sa.Column('systematic_emp', sa.Float(), nullable=True))
    op.add_column('equipment_calibration_result', sa.Column('random_error', sa.Float(), nullable=True))
    op.add_column('equipment_calibration_result', sa.Column('random_emp', sa.Float(), nullable=True))
    op.add_column('equipment_calibration_result', sa.Column('uncertainty_value', sa.Float(), nullable=True))
    op.add_column('equipment_calibration_result', sa.Column('k_value', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('equipment_calibration_result', 'k_value')
    op.drop_column('equipment_calibration_result', 'uncertainty_value')
    op.drop_column('equipment_calibration_result', 'random_emp')
    op.drop_column('equipment_calibration_result', 'random_error')
    op.drop_column('equipment_calibration_result', 'systematic_emp')
    op.drop_column('equipment_calibration_result', 'systematic_error')
    op.drop_column('equipment_calibration_result', 'volume_value')
