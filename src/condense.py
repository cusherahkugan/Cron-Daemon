import re
from html import escape

from lxml import html as lh

_SENT = re.compile(r"(?<=[.!?])\s+")
_JUNK = re.compile(r"^(last updated|comment|improve|suggest changes|share your thoughts|"
                   r"please login|article tags|like|report|related articles|"
                   r"table of contents|prerequisites?|open in app|explore|enhance your)", re.I)
IMG_COST = 350  # a diagram "costs" about this many characters of text


def _clip(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def condense(raw_html: str, char_budget: int, max_images: int = 2, embed=None,
             sentences: int = 2, list_items: int = 5, code_lines: int = 8) -> str:
    """Shrink an article to ~char_budget characters: headings, first N sentences of each
    paragraph, first few list items, short code snippets, small tables. Diagrams are
    always kept (up to max_images) even when the text budget runs out."""
    if not raw_html.strip():
        return ""
    try:
        root = lh.fragment_fromstring(raw_html, create_parent="div")
    except Exception:
        return ""
    out: list[str] = []
    used = imgs = 0
    seen_src: set[str] = set()
    for el in root:
        over = used >= char_budget
        if over and (imgs >= max_images or not embed):
            break
        tag = el.tag

        if tag in ("p", "img"):
            for img in ([el] if tag == "img" else el.iter("img")):
                src = img.get("src")
                if embed and imgs < max_images and src and src not in seen_src:
                    uri = embed(src)
                    if uri:
                        seen_src.add(src)
                        out.append(f'<img src="{uri}">')
                        imgs += 1
                        used += IMG_COST
            if tag == "p" and not over:
                text = " ".join(el.text_content().split())
                if len(text) >= 4 and not (len(text) < 40 and _JUNK.match(text)):
                    kept = _clip(" ".join(_SENT.split(text)[:sentences]), 120 * sentences + 20)
                    out.append(f"<p>{escape(kept)}</p>")
                    used += len(kept)
        elif over:
            continue
        elif tag in ("h2", "h3", "h4", "h5"):
            t = _clip(el.text_content(), 80)
            if t:
                out.append(f"<h4>{escape(t)}</h4>")
                used += len(t)
        elif tag in ("ul", "ol"):
            items = [_clip(li.text_content(), 110) for li in el.findall("li")][:list_items]
            items = [i for i in items if i]
            if items:
                out.append("<ul>" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>")
                used += sum(map(len, items))
        elif tag == "pre":
            lines = [l[:90] for l in el.text_content().strip().splitlines() if l.strip()][:code_lines]
            if lines:
                out.append("<pre>" + escape("\n".join(lines)) + "</pre>")
                used += sum(map(len, lines))
        elif tag == "table":
            rows = []
            for tr in el.findall(".//tr")[:5]:
                cells = [_clip(c.text_content(), 28) for c in tr if c.tag in ("td", "th")][:4]
                if any(cells):
                    rows.append("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in cells) + "</tr>")
            if rows:
                out.append("<table>" + "".join(rows) + "</table>")
                used += 120
    return "".join(out)