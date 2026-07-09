from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


class PublishAttempt(SQLModel, table=True):
    __tablename__ = "publish_attempts"
    __table_args__ = (
        UniqueConstraint(
            "platform_post_id",
            "platform",
            "scheduled_at",
            name="uq_publish_attempt_post_platform_scheduled_at",
        ),
    )

    idempotency_key: str = Field(max_length=255, primary_key=True)
    platform_post_id: int = Field(
        foreign_key="platform_posts.id",
        index=True,
        nullable=False,
    )
    platform: str = Field(max_length=40, nullable=False, index=True)
    scheduled_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    status: str = Field(default="publishing", max_length=40, nullable=False, index=True)
    attempt_count: int = Field(default=1, nullable=False)
    external_post_id: str | None = Field(default=None, max_length=255, index=True)
    external_post_url: str | None = Field(default=None, max_length=2048)
    error_message: str | None = Field(default=None)
    published_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
