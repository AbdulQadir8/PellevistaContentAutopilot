"""Add generation job and generated asset tables.

Revision ID: 20260708_0003
Revises: 20260708_0002
Create Date: 2026-07-08 00:00:02.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260708_0003"
down_revision: Union[str, Sequence[str], None] = "20260708_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_idea_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("reference_image_url", sa.String(length=2048), nullable=True),
        sa.Column("aspect_ratio", sa.String(length=20), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("creative_style", sa.String(length=255), nullable=False),
        sa.Column("higgsfield_request_id", sa.String(length=255), nullable=True),
        sa.Column("higgsfield_result_url", sa.String(length=2048), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["content_idea_id"],
            ["content_ideas.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generation_jobs_content_idea_id"),
        "generation_jobs",
        ["content_idea_id"],
    )
    op.create_index(op.f("ix_generation_jobs_platform"), "generation_jobs", ["platform"])
    op.create_index(op.f("ix_generation_jobs_status"), "generation_jobs", ["status"])

    op.create_table(
        "generated_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generation_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_idea_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("storage_url", sa.String(length=2048), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["content_idea_id"],
            ["content_ideas.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["generation_job_id"],
            ["generation_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generated_assets_content_idea_id"),
        "generated_assets",
        ["content_idea_id"],
    )
    op.create_index(
        op.f("ix_generated_assets_generation_job_id"),
        "generated_assets",
        ["generation_job_id"],
    )
    op.create_index(
        op.f("ix_generated_assets_platform"),
        "generated_assets",
        ["platform"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_assets_platform"), table_name="generated_assets")
    op.drop_index(
        op.f("ix_generated_assets_generation_job_id"),
        table_name="generated_assets",
    )
    op.drop_index(
        op.f("ix_generated_assets_content_idea_id"),
        table_name="generated_assets",
    )
    op.drop_table("generated_assets")

    op.drop_index(op.f("ix_generation_jobs_status"), table_name="generation_jobs")
    op.drop_index(op.f("ix_generation_jobs_platform"), table_name="generation_jobs")
    op.drop_index(
        op.f("ix_generation_jobs_content_idea_id"),
        table_name="generation_jobs",
    )
    op.drop_table("generation_jobs")
