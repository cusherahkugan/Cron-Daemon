from pdf_builder import build_pdf


def test_pdf_is_created(tmp_path):
    sections = [{
        "topic": "Docker",
        "subtopic": "Dockerfile",
        "articles": [{"title": "Demo", "url": "https://example.com", "html": "<p>Hello</p><pre>FROM ubuntu</pre>"}],
    }]
    out = tmp_path / "t.pdf"
    build_pdf("2026-10-22", sections, str(out))
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF")