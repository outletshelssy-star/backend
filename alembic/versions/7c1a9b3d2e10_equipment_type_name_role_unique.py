"""equipment type name role unique

Revision ID: 7c1a9b3d2e10
Revises: 3f2a1c9b7d8e
Create Date: 2026-02-05 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c1a9b3d2e10"
down_revision: Union[str, Sequence[str], None] = "3f2a1c9b7d8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                MIN(id) OVER (PARTITION BY name, role) AS keep_id
            FROM equipment_type
        ),
        dups AS (
            SELECT id, keep_id FROM ranked WHERE id <> keep_id
        )
        UPDATE equipment_type_measure etm
        SET equipment_type_id = d.keep_id
        FROM dups d
        WHERE etm.equipment_type_id = d.id;

        WITH ranked AS (
            SELECT
                id,
                MIN(id) OVER (PARTITION BY name, role) AS keep_id
            FROM equipment_type
        ),
        dups AS (
            SELECT id, keep_id FROM ranked WHERE id <> keep_id
        )
        UPDATE equipment_type_role_history etrh
        SET equipment_type_id = d.keep_id
        FROM dups d
        WHERE etrh.equipment_type_id = d.id;

        WITH ranked AS (
            SELECT
                id,
                MIN(id) OVER (PARTITION BY name, role) AS keep_id
            FROM equipment_type
        ),
        dups AS (
            SELECT id, keep_id FROM ranked WHERE id <> keep_id
        )
        UPDATE equipment_type_max_error etme
        SET equipment_type_id = d.keep_id
        FROM dups d
        WHERE etme.equipment_type_id = d.id;

        WITH ranked AS (
            SELECT
                id,
                MIN(id) OVER (PARTITION BY name, role) AS keep_id
            FROM equipment_type
        ),
        dups AS (
            SELECT id, keep_id FROM ranked WHERE id <> keep_id
        )
        UPDATE equipment_type_history eth
        SET equipment_type_id = d.keep_id
        FROM dups d
        WHERE eth.equipment_type_id = d.id;

        WITH ranked AS (
            SELECT
                id,
                MIN(id) OVER (PARTITION BY name, role) AS keep_id
            FROM equipment_type
        ),
        dups AS (
            SELECT id, keep_id FROM ranked WHERE id <> keep_id
        )
        UPDATE equipment e
        SET equipment_type_id = d.keep_id
        FROM dups d
        WHERE e.equipment_type_id = d.id;

        WITH ranked AS (
            SELECT
                id,
                MIN(id) OVER (PARTITION BY name, role) AS keep_id
            FROM equipment_type
        ),
        dups AS (
            SELECT id, keep_id FROM ranked WHERE id <> keep_id
        )
        DELETE FROM equipment_type
        WHERE id IN (SELECT id FROM dups);
        """
    )
    op.create_unique_constraint(
        "uq_equipment_type_name_role",
        "equipment_type",
        ["name", "role"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_equipment_type_name_role",
        "equipment_type",
        type_="unique",
    )
