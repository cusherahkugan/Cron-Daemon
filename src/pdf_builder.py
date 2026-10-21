import html as h

from weasyprint import HTML

from condense import condense
from scrape import embed_image

PAGE_MARGIN_MM = 2      # set 0 for truly edge-to-edge (most printers will clip it)
FONT_PT = 6.4

# (char budget per topic, max images, sentences/para, list items, code lines)
TIERS = [
    (4500, 2, 3, 6, 10),
    (3200, 2, 2, 5, 8),
    (2400, 2, 2, 5, 8),
    (1800, 1, 2, 4, 6),
    (1200, 1, 2, 3, 5),
    (800, 0, 2, 3, 4),
    (500, 0, 1, 3, 3),
    (300, 0, 1, 2, 2),
]


def _css(fs: float) -> str:
    return f"""
@page {{ size: A4; margin: {PAGE_MARGIN_MM}mm; }}
body {{ margin: 0; font-family: "DejaVu Sans", Arial, sans-serif; font-size: {fs}pt; line-height: 1.22; }}
h1 {{ font-size: {fs * 1.5:.1f}pt; margin: 0 0 1mm; border-bottom: 0.6pt solid #333; }}
.cols {{ column-count: 3; column-gap: 2.5mm; column-rule: 0.4pt solid #bbb; }}
.topic {{ margin: 0 0 1.8mm; }}
h2 {{ font-size: {fs * 1.2:.1f}pt; margin: 0; padding: 1px 3px; color: #fff; background: #1a5f2a; break-after: avoid; }}
h3 {{ font-size: {fs * 1.08:.1f}pt; margin: 1px 0; color: #0b3d91; break-after: avoid; }}
h4 {{ font-size: {fs}pt; margin: 2px 0 0; color: #333; break-after: avoid; }}
p {{ margin: 1px 0; }}
ul {{ margin: 1px 0; padding-left: 9px; }}
li {{ margin: 0; }}
pre {{ background: #f4f4f4; padding: 2px 3px; margin: 2px 0; white-space: pre-wrap; word-wrap: break-word;
      font-family: "DejaVu Sans Mono", monospace; font-size: {fs * 0.9:.1f}pt; line-height: 1.2;
      border-left: 2px solid #999; }}
img {{ display: block; max-width: 100%; max-height: 30mm; margin: 2px auto; }}
table {{ border-collapse: collapse; width: 100%; margin: 2px 0; font-size: {fs * 0.9:.1f}pt; }}
td {{ border: 0.4pt solid #aaa; padding: 0 2px; }}
.src {{ font-size: {fs * 0.75:.1f}pt; color: #777; word-break: break-all; }}
"""


def _render(date_str: str, sections: list[dict], tier: tuple, fs: float) -> str:
    budget, max_images, sentences, list_items, code_lines = tier
    parts = [f"<h1>Daily Study Notes - {h.escape(date_str)}</h1><div class='cols'>"]
    for s in sections:
        parts.append("<div class='topic'>")
        parts.append(f"<h2>{h.escape(s['topic'])}</h2><h3>{h.escape(s['subtopic'])}</h3>")
        body = condense(
            s.get("html", ""), budget, max_images,
            embed=lambda src, base=s.get("url", ""): embed_image(src, base),
            sentences=sentences, list_items=list_items, code_lines=code_lines,
        )
        parts.append(body or "<p><i>No content could be fetched today.</i></p>")
        if s.get("url"):
            parts.append(f"<div class='src'>{h.escape(s['url'])}</div>")
        parts.append("</div>")
    parts.append("</div>")
    return (f"<html><head><meta charset='utf-8'><style>{_css(fs)}</style></head>"
            f"<body>{''.join(parts)}</body></html>")


def build_pdf(date_str: str, sections: list[dict], out_path: str, max_pages: int = 6) -> int:
    """Use the richest content tier that fits in max_pages; shrink text, then font, if needed."""
    attempts = [(t, FONT_PT) for t in TIERS] + [(TIERS[-1], f) for f in (5.8, 5.4, 5.0)]
    doc = None
    for tier, fs in attempts:
        doc = HTML(string=_render(date_str, sections, tier, fs)).render()
        if len(doc.pages) <= max_pages:
            break
    doc.write_pdf(out_path)
    if len(doc.pages) > max_pages:
        print(f"WARNING: {len(doc.pages)} pages, above max_pages={max_pages}")
    return len(doc.pages)