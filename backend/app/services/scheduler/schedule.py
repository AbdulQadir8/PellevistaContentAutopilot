from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone

PELLEVISTA_LOCAL_TZ = timezone(timedelta(hours=5), name="PKT")


@dataclass(frozen=True, slots=True)
class PostScheduleSlot:
    set_number: int
    platform: str
    local_time: time
    scheduled_for: datetime


POST_SET_TIMES: tuple[tuple[tuple[str, time], ...], ...] = (
    (
        ("pinterest", time(18, 0)),
        ("instagram", time(18, 20)),
        ("facebook", time(18, 40)),
        ("x", time(19, 0)),
    ),
    (
        ("pinterest", time(22, 0)),
        ("instagram", time(22, 20)),
        ("facebook", time(22, 40)),
        ("x", time(23, 0)),
    ),
)


def build_daily_post_schedule(plan_date: date) -> list[PostScheduleSlot]:
    slots: list[PostScheduleSlot] = []
    for set_index, post_set in enumerate(POST_SET_TIMES, start=1):
        for platform, local_time in post_set:
            local_datetime = datetime.combine(
                plan_date,
                local_time,
                tzinfo=PELLEVISTA_LOCAL_TZ,
            )
            slots.append(
                PostScheduleSlot(
                    set_number=set_index,
                    platform=platform,
                    local_time=local_time,
                    scheduled_for=local_datetime.astimezone(UTC),
                ),
            )

    return slots


def slot_for_idea_platform(
    plan_date: date,
    idea_index: int,
    platform: str,
) -> PostScheduleSlot:
    normalized_platform = platform.lower()
    schedule = build_daily_post_schedule(plan_date)
    set_count = len(POST_SET_TIMES)
    set_number = (idea_index % set_count) + 1
    extra_days = idea_index // set_count

    for slot in schedule:
        if slot.set_number == set_number and slot.platform == normalized_platform:
            if extra_days == 0:
                return slot

            return PostScheduleSlot(
                set_number=slot.set_number,
                platform=slot.platform,
                local_time=slot.local_time,
                scheduled_for=slot.scheduled_for + timedelta(days=extra_days),
            )

    raise ValueError(f"Unsupported scheduled platform: {platform}")
