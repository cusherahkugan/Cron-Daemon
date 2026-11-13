from datetime import date

from config import get_day_index, pick_topic

NAMES = ["A", "B", "C"]


def test_day_index():
    assert get_day_index("2026-10-22", date(2026, 10, 22)) == 0
    assert get_day_index("2026-10-22", date(2026, 10, 24)) == 2
    assert get_day_index("2026-10-22", date(2026, 10, 21)) == -1


def test_pick_topic():
    assert pick_topic(NAMES, 0) == "A"
    assert pick_topic(NAMES, 2) == "C"


def test_before_start_or_after_last():
    assert pick_topic(NAMES, -1) is None
    assert pick_topic(NAMES, 3) is None