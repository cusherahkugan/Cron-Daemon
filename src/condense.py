import re
from html import escape

from lxml import html as lh

_SENT = re.compile(r"(?<=[.!?])\s+")
IMG_COST = 350  # a diagram "costs" about this many characters of text


def _clip(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def condense(raw_html: str, char_budget: int, max_images: int = 2, embed=None) -> str:
    """Shrink an article to ~char_budget characters: headings, first 2 sentences of each
    paragraph, first few list items, short code snippets. Diagrams are always kept
    (up to max_images) even when the text budget runs out."""
    if not raw_html.strip():
        return ""
    root = lh.fragment_fromstring(raw_html, create_parent="div")
    out: list[str] = []
    used = imgs = 0
    for el in root:
        over = used >= char_budget
        if over and (imgs >= max_images or not embed):
            break
        tag = el.tag

        if tag in ("p", "img"):
            for img in ([el] if tag == "img" else el.iter("img")):
                if embed and imgs < max_images:
                    uri = embed(img.get("src"))
                    if uri:
                        out.append(f'<img src="{uri}">')
                        imgs += 1
                        used += IMG_COST
            if tag == "p" and not over:
                text = " ".join(el.text_content().split())
                if text:
                    kept = _clip(" ".join(_SENT.split(text)[:2]), 260)
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
            items = [_clip(li.text_content(), 110) for li in el.findall("li")][:5]
            items = [i for i in items if i]
            if items:
                out.append("<ul>" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>")
                used += sum(map(len, items))
        elif tag == "pre":
            lines = [l[:90] for l in el.text_content().strip().splitlines() if l.strip()][:8]
            if lines:
                out.append("<pre>" + escape("\n".join(lines)) + "</pre>")
                used += sum(map(len, lines))
    return "".join(out)