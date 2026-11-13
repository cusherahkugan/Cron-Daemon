from pdf_builder import build_pdf
from slides_pdf import build_slides_pdf


def _chapters(n, paras=3):
    body = "".join("<h4>Heading</h4><p>Sentence one. Sentence two.</p>"
                   "<pre>FROM ubuntu\nRUN x</pre><p><a href='https://example.com'>link</a></p>"
                   for _ in range(paras))
    return [{"title": f"Article {i}", "url": "https://example.com", "body": body} for i in range(n)]


def test_a4_pdf_is_created(tmp_path):
    parts = build_pdf("2026-10-22", "Docker", "Day 1 of 15", _chapters(3), str(tmp_path / "a"))
    assert len(parts) == 1
    path, pages = parts[0]
    assert open(path, "rb").read(4) == b"%PDF" and pages >= 2


def test_slides_each_article_on_own_page(tmp_path):
    parts = build_slides_pdf("2026-10-22", "Docker", "Day 1 of 15", _chapters(4), str(tmp_path / "s"))
    assert parts[0][1] >= 5   # cover + one page per article at minimum


def test_nothing_is_cut_when_long(tmp_path):
    small = build_slides_pdf("2026-10-22", "X", "Day 1 of 15", _chapters(1, 3), str(tmp_path / "a"))
    big = build_slides_pdf("2026-10-22", "X", "Day 1 of 15", _chapters(1, 80), str(tmp_path / "b"))
    assert big[0][1] > small[0][1]


def test_splits_into_parts_under_the_limit(tmp_path):
    parts = build_slides_pdf("2026-10-22", "Java", "Day 1 of 15", _chapters(8), str(tmp_path / "j"), max_pages=4)
    assert len(parts) > 1
    assert all(n <= 4 for _, n in parts)
    assert all("_part" in p for p, _ in parts)