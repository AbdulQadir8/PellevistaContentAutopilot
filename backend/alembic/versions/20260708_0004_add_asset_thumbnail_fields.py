"""Add generated asset thumbnail fields.

Revision ID: 20260708_0004
Revises: 20260708_0003
Create Date: 2026-07-08 00:00:03.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260708_0004"
down_revision: Union[str, Sequence[str], None] = "20260708_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_assets",
        sa.Column("thumbnail_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "generated_assets",
        sa.Column("thumbnail_storage_key", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generated_assets", "thumbnail_storage_key")
    op.drop_column("generated_assets", "thumbnail_url")
