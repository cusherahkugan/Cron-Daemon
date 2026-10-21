import re

from lxml import html as lh

_JUNK = re.compile(r"^(?:last updated|comment|improve|suggest changes|share your thoughts|"
                   r"please login|article tags|like|report|related articles|"
                   r"table of contents|open in app|enhance your)\b", re.I)
_KEEP_ATTRS = {"colspan", "rowspan"}


def full_content(raw_html: str, embed=None, max_images: int = 15) -> str:
    """Clean an article for the PDF WITHOUT shortening it: every heading, paragraph,
    list, code block and table is kept. Only site junk is removed, links are flattened
    to plain text, and images are embedded (or dropped when they can't be)."""
    if not raw_html.strip():
        return ""
    try:
        root = lh.fragment_fromstring(raw_html, create_parent="div")
    except Exception:
        return ""

    for bad in root.xpath(".//script | .//style | .//iframe | .//noscript | .//form | .//button | .//svg"):
        bad.drop_tree()
    for a in root.xpath(".//a"):
        a.drop_tag()

    # images: embed (once each) or drop
    seen: set[str] = set()
    count = 0
    for img in list(root.iter("img")):
        src = img.get("src")
        uri = None
        if embed and src and src not in seen and count < max_images:
            uri = embed(src)
        if uri:
            seen.add(src)
            count += 1
            img.attrib.clear()
            img.set("src", uri)
        else:
            img.drop_tree()

    # junk / empty paragraphs
    for p in root.xpath(".//p"):
        text = " ".join(p.text_content().split())
        if p.xpath(".//img"):
            continue
        if len(text) < 4 or (len(text) < 40 and _JUNK.match(text)):
            p.drop_tree()

    # heading levels: h1/h2 -> h4, h3+ -> h5 (page-level h2/h3 are used by the layout)
    for el in root.xpath(".//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6"):
        el.tag = "h4" if el.tag in ("h1", "h2") else "h5"

    # strip attributes (classes, styles, widths...) so nothing can force overflow
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        for attr in list(el.attrib):
            if el.tag == "img" and attr == "src":
                continue
            if attr in _KEEP_ATTRS:
                continue
            del el.attrib[attr]

    return "".join(lh.tostring(c, encoding="unicode") for c in root)