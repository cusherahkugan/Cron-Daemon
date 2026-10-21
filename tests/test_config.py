from datetime import date

from config import get_day_index, pick_subtopics

TOPICS = {"A": ["a1", "a2", "a3"], "B": ["b1"]}


def test_day_index():
    assert get_day_index("2026-10-22", date(2026, 10, 22)) == 0
    assert get_day_index("2026-10-22", date(2026, 10, 24)) == 2
    assert get_day_index("2026-10-22", date(2026, 10, 21)) == -1


def test_pick_day_one():
    assert pick_subtopics(TOPICS, 0) == [("A", "a1"), ("B", "b1")]


def test_exhausted_topic_is_skipped():
    assert pick_subtopics(TOPICS, 1) == [("A", "a2")]


def test_only_filter():
    assert pick_subtopics(TOPICS, 0, only="b") == [("B", "b1")]


def test_before_start_or_after_end():
    assert pick_subtopics(TOPICS, -1) == []
    assert pick_subtopics(TOPICS, 10) == []