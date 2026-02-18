from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone

from src.config import Settings


@dataclass(frozen=True)
class ScheduleDecision:
    should_run_tests: bool
    should_send_mail: bool
    reason: str
    now_local: datetime


def _is_in_time_window(current: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def evaluate_schedule(settings: Settings, now_utc: datetime | None = None) -> ScheduleDecision:
    utc_now = now_utc.astimezone(timezone.utc) if now_utc else datetime.now(timezone.utc)
    now_local = utc_now.astimezone(settings.tzinfo)

    day_ok = now_local.strftime("%a") in settings.schedule_days
    time_ok = _is_in_time_window(now_local.time(), settings.schedule_start, settings.schedule_end)

    if day_ok and time_ok:
        return ScheduleDecision(
            should_run_tests=True,
            should_send_mail=True,
            reason="inside_schedule_window",
            now_local=now_local,
        )

    if settings.run_outside_schedule:
        return ScheduleDecision(
            should_run_tests=True,
            should_send_mail=False,
            reason="outside_schedule_window_mail_disabled",
            now_local=now_local,
        )

    return ScheduleDecision(
        should_run_tests=False,
        should_send_mail=False,
        reason="outside_schedule_window_skip_run",
        now_local=now_local,
    )
