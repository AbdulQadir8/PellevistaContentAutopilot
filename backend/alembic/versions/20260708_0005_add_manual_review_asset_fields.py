"""Add manual review fields to generated assets.

Revision ID: 20260708_0005
Revises: 20260708_0004
Create Date: 2026-07-08 00:00:04.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260708_0005"
down_revision: Union[str, Sequence[str], None] = "20260708_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_assets",
        sa.Column(
            "status",
            sa.String(length=40),
            nullable=False,
            server_default="generated",
        ),
    )
    op.add_column(
        "generated_assets",
        sa.Column("review_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "generated_assets",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        op.f("ix_generated_assets_status"),
        "generated_assets",
        ["status"],
        unique=False,
    )
    op.alter_column("generated_assets", "status", server_default=None)
    op.alter_column("generated_assets", "updated_at", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_assets_status"), table_name="generated_assets")
    op.drop_column("generated_assets", "updated_at")
    op.drop_column("generated_assets", "review_note")
    op.drop_column("generated_assets", "status")
