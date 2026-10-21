from condense import full_content
from scrape import extract_links

HTML = ("<h2>Intro</h2><p>One. Two. Three.</p><p><img src='a.png'></p><pre>"
        + "\n".join(f"line{i}" for i in range(30)) + "</pre>")


def test_nothing_is_trimmed():
    out = full_content(HTML)
    assert "Three" in out and "line29" in out


def test_images_embedded_or_dropped():
    assert "data:image/png" in full_content(HTML, embed=lambda s: "data:image/png;base64,AAAA")
    assert "<img" not in full_content(HTML, embed=lambda s: None)


def test_junk_removed_real_text_kept():
    out = full_content("<p>Last updated : 12 Jan, 2025</p><p>Real text here.</p>")
    assert "Last updated" not in out and "Real text here." in out


def test_extract_links_keeps_section_order():
    page = """<a href='/docker/what-is-docker/'>a</a><a href='/docker/dockerfile/#x'>b</a>
              <a href='/docker/what-is-docker/'>dup</a><a href='/java/oop/'>other</a>
              <a href='/docker/docker-interview-questions/'>skip</a><a href='/docker/docker-tutorial/'>self</a>"""
    got = extract_links(page, "https://www.geeksforgeeks.org/docker/docker-tutorial/")
    assert got == ["https://www.geeksforgeeks.org/docker/what-is-docker/",
                   "https://www.geeksforgeeks.org/docker/dockerfile/"]


def test_shared_section_requires_topic_keyword():
    page = """<a href='/devops/devops-tutorial/'>hub</a><a href='/devops/what-is-docker/'>a</a>
              <a href='/devops/kubernetes-architecture/'>k</a><a href='/devops/docker-tutorial/'>self</a>"""
    got = extract_links(page, "https://www.geeksforgeeks.org/devops/docker-tutorial/", "Docker")
    assert got == ["https://www.geeksforgeeks.org/devops/what-is-docker/"]