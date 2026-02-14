"""backfill external analysis default frequencies

Revision ID: 20260213_ext_analysis_defaults
Revises: 20260213_ext_analysis
Create Date: 2026-02-13
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '20260213_ext_analysis_defaults'
down_revision = '20260213_ext_analysis'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE external_analysis_type
        SET default_frequency_days = 720
        WHERE name = 'Assays' AND default_frequency_days = 0
        """
    )
    op.execute(
        """
        UPDATE external_analysis_type
        SET default_frequency_days = 180
        WHERE name = 'Cromatografia' AND default_frequency_days = 0
        """
    )
    op.execute(
        """
        UPDATE external_analysis_type
        SET default_frequency_days = 90
        WHERE name = 'Sedimentos' AND default_frequency_days = 0
        """
    )
    op.execute(
        """
        UPDATE external_analysis_type
        SET default_frequency_days = 180
        WHERE name = 'Azufre' AND default_frequency_days = 0
        """
    )
    op.execute(
        """
        UPDATE external_analysis_terminal AS t
        SET frequency_days = et.default_frequency_days
        FROM external_analysis_type AS et
        WHERE t.analysis_type_id = et.id AND t.frequency_days = 0
        """
    )


def downgrade() -> None:
    pass
