from pdf_builder import build_pdf


def _section(i, paras=80):
    body = "".join(f"<h2>Heading {j}</h2><p>Sentence one. Sentence two. Sentence three.</p><pre>FROM ubuntu\nRUN x</pre>"
                   for j in range(paras))
    return {"topic": f"T{i}", "subtopic": "Demo", "url": "https://example.com", "html": body}


def test_pdf_is_created(tmp_path):
    out = tmp_path / "t.pdf"
    build_pdf("2026-10-22", [_section(1, 1)], str(out))
    assert out.read_bytes().startswith(b"%PDF")


def test_page_cap_is_enforced(tmp_path):
    out = tmp_path / "t.pdf"
    pages = build_pdf("2026-10-22", [_section(i) for i in range(13)], str(out), max_pages=6)
    assert pages <= 6