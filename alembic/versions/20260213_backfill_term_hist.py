"""backfill equipment terminal history

Revision ID: 20260213_back_term_hist
Revises: 20260213_equ_term_hist
Create Date: 2026-02-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260213_back_term_hist"
down_revision: Union[str, Sequence[str], None] = "20260213_equ_term_hist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO equipment_terminal_history (
            equipment_id,
            terminal_id,
            started_at,
            ended_at,
            changed_by_user_id
        )
        SELECT
            e.id,
            e.terminal_id,
            e.created_at,
            NULL,
            e.created_by_user_id
        FROM equipment e
        WHERE NOT EXISTS (
            SELECT 1
            FROM equipment_terminal_history eth
            WHERE eth.equipment_id = e.id
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM equipment_terminal_history
        WHERE id IN (
            SELECT eth.id
            FROM equipment_terminal_history eth
            JOIN equipment e ON e.id = eth.equipment_id
            WHERE eth.started_at = e.created_at
              AND eth.ended_at IS NULL
              AND eth.changed_by_user_id = e.created_by_user_id
        )
        """
    )
