"""Add publish attempts idempotency table.

Revision ID: 20260708_0008
Revises: 20260708_0007
Create Date: 2026-07-08 00:00:07.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260708_0008"
down_revision: Union[str, Sequence[str], None] = "20260708_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "publish_attempts",
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("platform_post_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("external_post_id", sa.String(length=255), nullable=True),
        sa.Column("external_post_url", sa.String(length=2048), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["platform_post_id"],
            ["platform_posts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("idempotency_key"),
        sa.UniqueConstraint(
            "platform_post_id",
            "platform",
            "scheduled_at",
            name="uq_publish_attempt_post_platform_scheduled_at",
        ),
    )
    op.create_index(
        op.f("ix_publish_attempts_external_post_id"),
        "publish_attempts",
        ["external_post_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publish_attempts_platform"),
        "publish_attempts",
        ["platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publish_attempts_platform_post_id"),
        "publish_attempts",
        ["platform_post_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publish_attempts_published_at"),
        "publish_attempts",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publish_attempts_scheduled_at"),
        "publish_attempts",
        ["scheduled_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publish_attempts_status"),
        "publish_attempts",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_publish_attempts_status"), table_name="publish_attempts")
    op.drop_index(op.f("ix_publish_attempts_scheduled_at"), table_name="publish_attempts")
    op.drop_index(op.f("ix_publish_attempts_published_at"), table_name="publish_attempts")
    op.drop_index(op.f("ix_publish_attempts_platform_post_id"), table_name="publish_attempts")
    op.drop_index(op.f("ix_publish_attempts_platform"), table_name="publish_attempts")
    op.drop_index(op.f("ix_publish_attempts_external_post_id"), table_name="publish_attempts")
    op.drop_table("publish_attempts")
