from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TOURGW_BASE_URL = "https://tourgwcore.azurewebsites.net/Deals/Search"
ESHET_BASE_URL = "https://www.eshet.com/flight-hotel/searchresults"

TARGET_DESTINATION_CODE = "50022"
TARGET_DESTINATION_NAME_HE = "בטומי"
SABRE_VENDOR = "SabreLDS"
ODYSSEA_VENDOR = "Odyssea"

TOURGW_STATIC_QUERY = {
    "destinationCode": TARGET_DESTINATION_CODE,
    "dealType": "Deal",
    "SubjectId": "0",
    "hotelCode": "",
    "adults": "2",
    "children": "0",
    "infants": "0",
    "isAgent": "false",
    "isTravelList": "false",
}

ESHET_STATIC_QUERY = {
    "origin": "53492",
    "destination": TARGET_DESTINATION_CODE,
    "r0": "2_",
    "subject": "27",
    "dealDates": "true",
}


WEEKDAY_ALIASES = {
    "sun": "Sun",
    "sunday": "Sun",
    "mon": "Mon",
    "monday": "Mon",
    "tue": "Tue",
    "tues": "Tue",
    "tuesday": "Tue",
    "wed": "Wed",
    "wednesday": "Wed",
    "thu": "Thu",
    "thur": "Thu",
    "thurs": "Thu",
    "thursday": "Thu",
    "fri": "Fri",
    "friday": "Fri",
    "sat": "Sat",
    "saturday": "Sat",
}


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_time(value: str, env_name: str) -> time:
    raw = value.strip()
    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(f"{env_name} must be HH:MM, got: {raw}")

    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"{env_name} has invalid time: {raw}")

    return time(hour=hour, minute=minute)


def parse_days(value: str | None) -> set[str]:
    if not value:
        return {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri"}

    result: set[str] = set()
    for raw in value.split(","):
        token = raw.strip().lower()
        if not token:
            continue
        mapped = WEEKDAY_ALIASES.get(token)
        if not mapped:
            raise ValueError(f"Unsupported day in SCHEDULE_DAYS: {raw}")
        result.add(mapped)

    if not result:
        raise ValueError("SCHEDULE_DAYS cannot be empty")

    return result


@dataclass(frozen=True)
class Settings:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str = field(repr=False)
    mail_to: list[str]
    mail_cc: list[str]
    schedule_tz: str
    schedule_days: set[str]
    schedule_start: time
    schedule_end: time
    run_outside_schedule: bool
    headless: bool
    eshet_results_wait_ms: int
    eshet_scroll_wait_ms: int
    eshet_max_scrolls: int

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.schedule_tz)

    def smtp_ready(self) -> bool:
        return all(
            [
                self.smtp_host.strip(),
                self.smtp_user.strip(),
                self.smtp_pass.strip(),
                self.smtp_port > 0,
                bool(self.mail_to),
            ]
        )


def load_settings() -> Settings:
    smtp_port_raw = os.getenv("SMTP_PORT", "587").strip()
    smtp_port = int(smtp_port_raw)

    schedule_tz = os.getenv("SCHEDULE_TZ", "Asia/Jerusalem").strip()
    schedule_days = parse_days(os.getenv("SCHEDULE_DAYS", "Sun,Mon,Tue,Wed,Thu,Fri"))
    schedule_start = parse_time(os.getenv("SCHEDULE_START", "08:00"), "SCHEDULE_START")
    schedule_end = parse_time(os.getenv("SCHEDULE_END", "17:00"), "SCHEDULE_END")

    return Settings(
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=smtp_port,
        smtp_user=os.getenv("SMTP_USER", "").strip(),
        smtp_pass=os.getenv("SMTP_PASS", "").strip(),
        mail_to=parse_csv(os.getenv("MAIL_TO", "")),
        mail_cc=parse_csv(os.getenv("MAIL_CC", "")),
        schedule_tz=schedule_tz,
        schedule_days=schedule_days,
        schedule_start=schedule_start,
        schedule_end=schedule_end,
        run_outside_schedule=parse_bool(os.getenv("RUN_OUTSIDE_SCHEDULE", "false"), default=False),
        headless=parse_bool(os.getenv("HEADLESS", "true"), default=True),
        eshet_results_wait_ms=12_000,
        eshet_scroll_wait_ms=2_000,
        eshet_max_scrolls=8,
    )
