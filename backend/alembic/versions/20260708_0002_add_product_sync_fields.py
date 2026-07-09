"""Add product sync fields.

Revision ID: 20260708_0002
Revises: 20260708_0001
Create Date: 2026-07-08 00:00:01.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260708_0002"
down_revision: Union[str, Sequence[str], None] = "20260708_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("price", sa.String(length=40), nullable=True))
    op.add_column(
        "products",
        sa.Column("currency_code", sa.String(length=10), nullable=True),
    )
    op.add_column("products", sa.Column("total_inventory", sa.Integer(), nullable=True))
    op.add_column(
        "products",
        sa.Column(
            "available_for_sale",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "has_image",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "eligible_for_content",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "products",
        sa.Column("priority_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "products",
        sa.Column("last_posted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_products_eligible_for_content"),
        "products",
        ["eligible_for_content"],
    )
    op.create_index(
        op.f("ix_products_last_posted_at"),
        "products",
        ["last_posted_at"],
    )
    op.create_index(
        op.f("ix_products_priority_score"),
        "products",
        ["priority_score"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_products_priority_score"), table_name="products")
    op.drop_index(op.f("ix_products_last_posted_at"), table_name="products")
    op.drop_index(op.f("ix_products_eligible_for_content"), table_name="products")
    op.drop_column("products", "last_synced_at")
    op.drop_column("products", "last_posted_at")
    op.drop_column("products", "priority_score")
    op.drop_column("products", "eligible_for_content")
    op.drop_column("products", "has_image")
    op.drop_column("products", "available_for_sale")
    op.drop_column("products", "total_inventory")
    op.drop_column("products", "currency_code")
    op.drop_column("products", "price")
