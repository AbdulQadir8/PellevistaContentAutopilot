from datetime import UTC, date, datetime, time

from app.services.scheduler import build_daily_post_schedule, slot_for_idea_platform
from app.workers.celery_app import celery_app


def test_pellevista_post_schedule_converts_pkt_slots_to_utc() -> None:
    schedule = build_daily_post_schedule(date(2026, 7, 9))

    assert [
        (slot.set_number, slot.platform, slot.local_time, slot.scheduled_for)
        for slot in schedule
    ] == [
        (
            1,
            "pinterest",
            time(18, 0),
            datetime(2026, 7, 9, 13, 0, tzinfo=UTC),
        ),
        (
            1,
            "instagram",
            time(18, 20),
            datetime(2026, 7, 9, 13, 20, tzinfo=UTC),
        ),
        (
            1,
            "facebook",
            time(18, 40),
            datetime(2026, 7, 9, 13, 40, tzinfo=UTC),
        ),
        (1, "x", time(19, 0), datetime(2026, 7, 9, 14, 0, tzinfo=UTC)),
        (
            2,
            "pinterest",
            time(22, 0),
            datetime(2026, 7, 9, 17, 0, tzinfo=UTC),
        ),
        (
            2,
            "instagram",
            time(22, 20),
            datetime(2026, 7, 9, 17, 20, tzinfo=UTC),
        ),
        (
            2,
            "facebook",
            time(22, 40),
            datetime(2026, 7, 9, 17, 40, tzinfo=UTC),
        ),
        (2, "x", time(23, 0), datetime(2026, 7, 9, 18, 0, tzinfo=UTC)),
    ]
    assert len({slot.scheduled_for for slot in schedule}) == len(schedule)


def test_slot_for_idea_platform_uses_separate_sets() -> None:
    first_set = slot_for_idea_platform(
        plan_date=date(2026, 7, 9),
        idea_index=0,
        platform="Instagram",
    )
    second_set = slot_for_idea_platform(
        plan_date=date(2026, 7, 9),
        idea_index=1,
        platform="Instagram",
    )

    assert first_set.scheduled_for == datetime(2026, 7, 9, 13, 20, tzinfo=UTC)
    assert second_set.scheduled_for == datetime(2026, 7, 9, 17, 20, tzinfo=UTC)


def test_celery_beat_schedule_uses_utc_daily_jobs() -> None:
    beat_schedule = celery_app.conf.beat_schedule

    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True
    assert set(beat_schedule) >= {
        "daily-shopify-sync",
        "daily-content-plan",
        "daily-asset-generation",
        "daily-post-preparation",
        "publish-due-scheduled-posts",
        "collect-due-analytics",
    }
    assert beat_schedule["daily-shopify-sync"]["task"] == (
        "app.workers.tasks.sync_shopify_products"
    )
    assert beat_schedule["daily-shopify-sync"]["schedule"]._orig_hour == 0
    assert beat_schedule["daily-shopify-sync"]["schedule"]._orig_minute == 5
    assert beat_schedule["daily-content-plan"]["schedule"]._orig_hour == 0
    assert beat_schedule["daily-content-plan"]["schedule"]._orig_minute == 15
    assert beat_schedule["daily-asset-generation"]["schedule"]._orig_hour == 0
    assert beat_schedule["daily-asset-generation"]["schedule"]._orig_minute == 30
    assert beat_schedule["daily-post-preparation"]["schedule"]._orig_hour == 2
    assert beat_schedule["daily-post-preparation"]["schedule"]._orig_minute == 0
    assert beat_schedule["publish-due-scheduled-posts"]["schedule"]._orig_minute == "*"
    assert beat_schedule["collect-due-analytics"]["task"] == (
        "app.workers.tasks.collect_due_analytics"
    )
    assert beat_schedule["collect-due-analytics"]["schedule"]._orig_minute == "*/15"
