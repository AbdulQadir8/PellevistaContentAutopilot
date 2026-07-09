"""Create initial content tables.

Revision ID: 20260708_0001
Revises:
Create Date: 2026-07-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260708_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("shopify_domain", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brands_slug"), "brands", ["slug"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("shopify_product_id", sa.String(length=128), nullable=False),
        sa.Column("handle", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("vendor", sa.String(length=255), nullable=True),
        sa.Column("product_type", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shopify_product_id"),
    )
    op.create_index(op.f("ix_products_brand_id"), "products", ["brand_id"])
    op.create_index(op.f("ix_products_handle"), "products", ["handle"])
    op.create_index(op.f("ix_products_status"), "products", ["status"])

    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("shopify_image_id", sa.String(length=128), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("alt_text", sa.String(length=500), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shopify_image_id"),
    )
    op.create_index(
        op.f("ix_product_images_product_id"),
        "product_images",
        ["product_id"],
    )

    op.create_table(
        "content_ideas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("angle", sa.String(length=500), nullable=False),
        sa.Column("brief", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_content_ideas_brand_id"), "content_ideas", ["brand_id"])
    op.create_index(op.f("ix_content_ideas_product_id"), "content_ideas", ["product_id"])
    op.create_index(op.f("ix_content_ideas_status"), "content_ideas", ["status"])

    op.create_table(
        "platform_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content_idea_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("draft_caption", sa.Text(), nullable=False),
        sa.Column("draft_media_url", sa.String(length=2048), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["content_idea_id"],
            ["content_ideas.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_platform_posts_content_idea_id"),
        "platform_posts",
        ["content_idea_id"],
    )
    op.create_index(op.f("ix_platform_posts_platform"), "platform_posts", ["platform"])
    op.create_index(op.f("ix_platform_posts_product_id"), "platform_posts", ["product_id"])
    op.create_index(
        op.f("ix_platform_posts_scheduled_for"),
        "platform_posts",
        ["scheduled_for"],
    )
    op.create_index(op.f("ix_platform_posts_status"), "platform_posts", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_platform_posts_status"), table_name="platform_posts")
    op.drop_index(op.f("ix_platform_posts_scheduled_for"), table_name="platform_posts")
    op.drop_index(op.f("ix_platform_posts_product_id"), table_name="platform_posts")
    op.drop_index(op.f("ix_platform_posts_platform"), table_name="platform_posts")
    op.drop_index(
        op.f("ix_platform_posts_content_idea_id"),
        table_name="platform_posts",
    )
    op.drop_table("platform_posts")

    op.drop_index(op.f("ix_content_ideas_status"), table_name="content_ideas")
    op.drop_index(op.f("ix_content_ideas_product_id"), table_name="content_ideas")
    op.drop_index(op.f("ix_content_ideas_brand_id"), table_name="content_ideas")
    op.drop_table("content_ideas")

    op.drop_index(op.f("ix_product_images_product_id"), table_name="product_images")
    op.drop_table("product_images")

    op.drop_index(op.f("ix_products_status"), table_name="products")
    op.drop_index(op.f("ix_products_handle"), table_name="products")
    op.drop_index(op.f("ix_products_brand_id"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_brands_slug"), table_name="brands")
    op.drop_table("brands")
