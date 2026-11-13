import html as h

from condense import full_content
from scrape import embed_image


def build_chapters(articles: list[dict]) -> list[dict]:
    """articles: [{title, url, html}] -> [{title, url, body}] with cleaned, full content."""
    chapters = []
    for a in articles:
        body = full_content(
            a.get("html", ""),
            embed=lambda src, base=a["url"]: embed_image(src, base),
            keep_links=True,
            base_url=a["url"],
        )
        if body.strip():
            chapters.append({"title": a["title"], "url": a["url"], "body": body})
    return chapters


def cover_html(topic: str, date_str: str, day_label: str, chapters: list[dict]) -> str:
    toc = "".join(f"<li>{h.escape(c['title'])}</li>" for c in chapters)
    return (f"<section class='cover'><h1 class='tname'>{h.escape(topic)}</h1>"
            f"<p class='date'>{h.escape(day_label)} &middot; {h.escape(date_str)} "
            f"&middot; {len(chapters)} articles</p><ol>{toc}</ol></section>")


def chapters_html(chapters: list[dict]) -> str:
    out = []
    for c in chapters:
        out.append(f"<section class='chap'><h3 class='art'>{h.escape(c['title'])}</h3>"
                   f"<div class='rule'></div>{c['body']}"
                   f"<div class='src'>{h.escape(c['url'])}</div></section>")
    return "".join(out)