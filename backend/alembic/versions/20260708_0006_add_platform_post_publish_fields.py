"""Add platform post publishing result fields.

Revision ID: 20260708_0006
Revises: 20260708_0005
Create Date: 2026-07-08 00:00:05.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260708_0006"
down_revision: Union[str, Sequence[str], None] = "20260708_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_posts",
        sa.Column("external_post_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "platform_posts",
        sa.Column("external_post_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "platform_posts",
        sa.Column("publish_error", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_platform_posts_external_post_id"),
        "platform_posts",
        ["external_post_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_platform_posts_external_post_id"), table_name="platform_posts")
    op.drop_column("platform_posts", "publish_error")
    op.drop_column("platform_posts", "external_post_url")
    op.drop_column("platform_posts", "external_post_id")
