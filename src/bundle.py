import html as h

from weasyprint import HTML

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


def cover_html(topic: str, date_str: str, day_label: str, chapters: list[dict],
               part_label: str = "") -> str:
    toc = "".join(f"<li>{h.escape(c['title'])}</li>" for c in chapters)
    extra = f" &middot; {h.escape(part_label)}" if part_label else ""
    return (f"<section class='cover'><h1 class='tname'>{h.escape(topic)}</h1>"
            f"<p class='date'>{h.escape(day_label)} &middot; {h.escape(date_str)}{extra} "
            f"&middot; {len(chapters)} articles</p><ol>{toc}</ol></section>")


def chapters_html(chapters: list[dict]) -> str:
    out = []
    for c in chapters:
        out.append(f"<section class='chap'><h3 class='art'>{h.escape(c['title'])}</h3>"
                   f"<div class='rule'></div>{c['body']}"
                   f"<div class='src'>{h.escape(c['url'])}</div></section>")
    return "".join(out)


def _wrap(css: str, body: str) -> str:
    return f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"


def build_parts(css: str, topic: str, date_str: str, day_label: str, chapters: list[dict],
                out_stem: str, max_pages: int = 500) -> list[tuple[str, int]]:
    """Write one or more PDFs of at most `max_pages` pages each (split between articles only).
    Returns [(path, pages)]."""
    # 1) estimate pages per article (rendered alone, no cover)
    est = [len(HTML(string=_wrap(css, chapters_html([c]))).render().pages) for c in chapters]
    multi = sum(est) + 1 > max_pages

    results: list[tuple[str, int]] = []
    start, part_no = 0, 0
    while start < len(chapters):
        part_no += 1
        # 2) greedy pack by estimate (1 page reserved for the cover)
        end, used = start, 1
        while end < len(chapters) and (end == start or used + est[end] <= max_pages):
            used += est[end]
            end += 1

        # 3) real render; if it is over the limit, push the last article to the next part
        while True:
            part = chapters[start:end]
            label = f"Part {part_no}" if multi else ""
            body = cover_html(topic, date_str, day_label, part, label) + chapters_html(part)
            doc = HTML(string=_wrap(css, body)).render()
            if len(doc.pages) <= max_pages or len(part) == 1:
                break
            end -= 1

        path = f"{out_stem}_part{part_no}.pdf" if multi else f"{out_stem}.pdf"
        doc.write_pdf(path)
        results.append((path, len(doc.pages)))
        start = end
    return results