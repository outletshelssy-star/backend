"""add volume to equipmentmeasuretype and migrate kf data

Revision ID: 20260305_add_volume_measure
Revises: 20260305_equ_status_hist
Create Date: 2026-03-05
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260305_add_volume_measure"
down_revision = "20260305_equ_status_hist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE equipmentmeasuretype ADD VALUE IF NOT EXISTS 'volume'")

    op.execute(
        """
        UPDATE equipment_type_measure etm
        SET measure = 'volume'::equipmentmeasuretype
        FROM equipment_type et
        WHERE etm.equipment_type_id = et.id
          AND etm.measure = 'percent_pv'::equipmentmeasuretype
          AND lower(et.name) = 'titulador karl fischer'
        """
    )

    op.execute(
        """
        UPDATE equipment_type_max_error etme
        SET measure = 'volume'::equipmentmeasuretype
        FROM equipment_type et
        WHERE etme.equipment_type_id = et.id
          AND etme.measure = 'percent_pv'::equipmentmeasuretype
          AND lower(et.name) = 'titulador karl fischer'
        """
    )

    op.execute(
        """
        UPDATE equipment_measure_spec ems
        SET measure = 'volume'::equipmentmeasuretype
        FROM equipment e
        JOIN equipment_type et ON et.id = e.equipment_type_id
        WHERE ems.equipment_id = e.id
          AND ems.measure = 'percent_pv'::equipmentmeasuretype
          AND lower(et.name) = 'titulador karl fischer'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE equipment_type_measure etm
        SET measure = 'percent_pv'::equipmentmeasuretype
        FROM equipment_type et
        WHERE etm.equipment_type_id = et.id
          AND etm.measure = 'volume'::equipmentmeasuretype
          AND lower(et.name) = 'titulador karl fischer'
        """
    )

    op.execute(
        """
        UPDATE equipment_type_max_error etme
        SET measure = 'percent_pv'::equipmentmeasuretype
        FROM equipment_type et
        WHERE etme.equipment_type_id = et.id
          AND etme.measure = 'volume'::equipmentmeasuretype
          AND lower(et.name) = 'titulador karl fischer'
        """
    )

    op.execute(
        """
        UPDATE equipment_measure_spec ems
        SET measure = 'percent_pv'::equipmentmeasuretype
        FROM equipment e
        JOIN equipment_type et ON et.id = e.equipment_type_id
        WHERE ems.equipment_id = e.id
          AND ems.measure = 'volume'::equipmentmeasuretype
          AND lower(et.name) = 'titulador karl fischer'
        """
    )

    # Postgres enum values are not removed in downgrade.
