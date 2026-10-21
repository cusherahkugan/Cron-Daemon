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


def pick_subtopics(topics: dict, day_index: int, only: str | None = None) -> list[tuple[str, str]]:
    """Return [(topic, subtopic)] for the given day. Topics that ran out are skipped."""
    picked = []
    for topic, subs in topics.items():
        if only and only.lower() != topic.lower():
            continue
        if 0 <= day_index < len(subs):
            picked.append((topic, subs[day_index]))
    return picked