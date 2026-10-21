from condense import condense
from scrape import extract_links

HTML = "<h2>Intro</h2><p>One. Two. Three.</p><p><img src='a.png'></p><pre>" + "\n".join(f"line{i}" for i in range(30)) + "</pre>"


def test_text_trimmed_and_code_capped():
    out = condense(HTML, 5000)
    assert "Three" not in out
    assert "line7" in out and "line8" not in out


def test_diagram_kept_even_when_budget_exhausted():
    out = condense(HTML, 1, max_images=1, embed=lambda s: "data:image/png;base64,AAAA")
    assert "<img" in out


def test_extract_links_keeps_section_order():
    page = """<a href='/docker/what-is-docker/'>a</a><a href='/docker/dockerfile/#x'>b</a>
              <a href='/docker/what-is-docker/'>dup</a><a href='/java/oop/'>other</a>
              <a href='/docker/docker-interview-questions/'>skip</a><a href='/docker/docker-tutorial/'>self</a>"""
    got = extract_links(page, "https://www.geeksforgeeks.org/docker/docker-tutorial/")
    assert got == ["https://www.geeksforgeeks.org/docker/what-is-docker/",
                   "https://www.geeksforgeeks.org/docker/dockerfile/"]