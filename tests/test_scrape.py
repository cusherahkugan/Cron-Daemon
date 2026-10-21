import scrape
from scrape import _prepare


def test_code_block_keeps_newlines():
    html = "<html><body><div class='highlight'><ol><li>x = 1</li><li>print(x)</li></ol></div></body></html>"
    assert "<pre>x = 1\nprint(x)</pre>" in _prepare(html)


def test_resolve_skips_bad_candidate(tmp_path, monkeypatch):
    page = "".join(f"<a href='/docker/topic-{i}/'>t{i}</a>" for i in range(10))
    monkeypatch.setattr(scrape, "_get", lambda url: page if "good" in url else "<p>none</p>")
    url, links = scrape.resolve_topic(
        "Docker",
        ["https://www.geeksforgeeks.org/bad/docker/", "https://www.geeksforgeeks.org/docker/good/"],
        lambda t: [],
        cache_path=str(tmp_path / "c.json"),
    )
    assert url.endswith("/docker/good/") and len(links) == 10