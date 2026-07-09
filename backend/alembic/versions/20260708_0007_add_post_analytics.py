"""Add post analytics tables.

Revision ID: 20260708_0007
Revises: 20260708_0006
Create Date: 2026-07-08 00:00:06.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260708_0007"
down_revision: Union[str, Sequence[str], None] = "20260708_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_posts",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_platform_posts_published_at"),
        "platform_posts",
        ["published_at"],
        unique=False,
    )
    op.create_table(
        "post_analytics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform_post_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("external_post_id", sa.String(length=255), nullable=False),
        sa.Column("external_post_url", sa.String(length=2048), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("content_pillar", sa.String(length=255), nullable=False),
        sa.Column("collection_label", sa.String(length=40), nullable=False),
        sa.Column("collection_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("saves", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["platform_post_id"],
            ["platform_posts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "platform_post_id",
            "collection_label",
            name="uq_post_analytics_post_collection",
        ),
    )
    op.create_index(
        op.f("ix_post_analytics_collected_at"),
        "post_analytics",
        ["collected_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_post_analytics_collection_due_at"),
        "post_analytics",
        ["collection_due_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_post_analytics_collection_label"),
        "post_analytics",
        ["collection_label"],
        unique=False,
    )
    op.create_index(
        op.f("ix_post_analytics_content_pillar"),
        "post_analytics",
        ["content_pillar"],
        unique=False,
    )
    op.create_index(
        op.f("ix_post_analytics_external_post_id"),
        "post_analytics",
        ["external_post_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_post_analytics_platform"),
        "post_analytics",
        ["platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_post_analytics_platform_post_id"),
        "post_analytics",
        ["platform_post_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_post_analytics_product_id"),
        "post_analytics",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_post_analytics_published_at"),
        "post_analytics",
        ["published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_post_analytics_published_at"), table_name="post_analytics")
    op.drop_index(op.f("ix_post_analytics_product_id"), table_name="post_analytics")
    op.drop_index(op.f("ix_post_analytics_platform_post_id"), table_name="post_analytics")
    op.drop_index(op.f("ix_post_analytics_platform"), table_name="post_analytics")
    op.drop_index(op.f("ix_post_analytics_external_post_id"), table_name="post_analytics")
    op.drop_index(op.f("ix_post_analytics_content_pillar"), table_name="post_analytics")
    op.drop_index(op.f("ix_post_analytics_collection_label"), table_name="post_analytics")
    op.drop_index(op.f("ix_post_analytics_collection_due_at"), table_name="post_analytics")
    op.drop_index(op.f("ix_post_analytics_collected_at"), table_name="post_analytics")
    op.drop_table("post_analytics")
    op.drop_index(op.f("ix_platform_posts_published_at"), table_name="platform_posts")
    op.drop_column("platform_posts", "published_at")
