from pdf_builder import build_pdf
from slides_pdf import build_slides_pdf


def _chapters(n, paras=3):
    body = "".join("<h4>Heading</h4><p>Sentence one. Sentence two.</p>"
                   "<pre>FROM ubuntu\nRUN x</pre><p><a href='https://example.com'>link</a></p>"
                   for _ in range(paras))
    return [{"title": f"Article {i}", "url": "https://example.com", "body": body} for i in range(n)]


def test_a4_pdf_is_created(tmp_path):
    out = tmp_path / "a.pdf"
    pages = build_pdf("2026-10-22", "Docker", "Day 1 of 15", _chapters(3), str(out))
    assert out.read_bytes().startswith(b"%PDF") and pages >= 2


def test_slides_each_article_on_own_page(tmp_path):
    out = tmp_path / "s.pdf"
    pages = build_slides_pdf("2026-10-22", "Docker", "Day 1 of 15", _chapters(4), str(out))
    assert pages >= 5   # cover + one page per article at minimum


def test_nothing_is_cut_when_long(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    n_small = build_slides_pdf("2026-10-22", "X", "Day 1 of 15", _chapters(1, 3), str(a))
    n_big = build_slides_pdf("2026-10-22", "X", "Day 1 of 15", _chapters(1, 80), str(b))
    assert n_big > n_small