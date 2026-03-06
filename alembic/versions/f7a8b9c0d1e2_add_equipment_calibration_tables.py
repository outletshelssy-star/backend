"""add equipment calibration tables

Revision ID: f7a8b9c0d1e2
Revises: e6f1a2b3c4d5
Create Date: 2026-02-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "equipment_calibration",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("calibration_company_id", sa.Integer(), nullable=True),
        sa.Column(
            "calibration_company_name",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column(
            "certificate_pdf_url",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["calibration_company_id"], ["company.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "equipment_calibration_result",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("calibration_id", sa.Integer(), nullable=False),
        sa.Column("point_label", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("reference_value", sa.Float(), nullable=True),
        sa.Column("measured_value", sa.Float(), nullable=True),
        sa.Column("unit", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("error_value", sa.Float(), nullable=True),
        sa.Column("tolerance_value", sa.Float(), nullable=True),
        sa.Column("is_ok", sa.Boolean(), nullable=True),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["calibration_id"],
            ["equipment_calibration.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("equipment_calibration_result")
    op.drop_table("equipment_calibration")
