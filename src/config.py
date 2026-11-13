from datetime import date, datetime
from zoneinfo import ZoneInfo

import yaml


def load_config(path: str = "config/topics.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def today_in_tz(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


def get_day_index(start_date: str, today: date) -> int:
    """0 for Day 1, 1 for Day 2, ... (negative if before start_date)."""
    return (today - date.fromisoformat(start_date)).days


def pick_topic(topics: list[str], day_index: int) -> str | None:
    """Day 1 -> first topic, Day 2 -> second ... None when before the start or all topics are done."""
    return topics[day_index] if 0 <= day_index < len(topics) else None