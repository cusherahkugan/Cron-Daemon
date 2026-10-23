from slides_pdf import build_slides_pdf


def _section(i, paras=1):
    body = "".join(
        f"<h2>Heading {j}</h2><p>Sentence one. Sentence two. Sentence three.</p>"
        f"<ul><li>point a</li><li>point b</li></ul><pre>FROM ubuntu\nRUN x</pre>"
        f"<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        for j in range(paras))
    return {"topic": f"T{i}", "subtopic": "Demo", "url": "https://example.com", "html": body}


def test_slides_pdf_is_created(tmp_path):
    out = tmp_path / "s.pdf"
    pages = build_slides_pdf("2026-10-22", [_section(1)], str(out))
    assert out.read_bytes().startswith(b"%PDF") and pages >= 2   # cover + topic


def test_each_topic_starts_on_its_own_page(tmp_path):
    out = tmp_path / "s.pdf"
    pages = build_slides_pdf("2026-10-22", [_section(i) for i in range(4)], str(out))
    assert pages >= 5   # cover + one page per topic


def test_nothing_is_cut_when_content_is_long(tmp_path):
    small, big = tmp_path / "a.pdf", tmp_path / "b.pdf"
    n_small = build_slides_pdf("2026-10-22", [_section(1, 5)], str(small))
    n_big = build_slides_pdf("2026-10-22", [_section(1, 80)], str(big))
    assert n_big > n_small   # extra pages are added instead of trimming content


def test_failed_fetch_gets_placeholder_page(tmp_path):
    out = tmp_path / "s.pdf"
    sec = {"topic": "X", "subtopic": "http://x", "url": "http://x", "html": ""}
    assert build_slides_pdf("2026-10-22", [sec], str(out)) == 2