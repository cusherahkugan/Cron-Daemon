import html as h
import re

from weasyprint import HTML

from condense import full_content
from scrape import embed_image

PAGE_MARGIN_MM = 4
FONT_SIZES = [7.5, 7.0, 6.6, 6.2, 5.8, 5.4, 5.0]   # tried largest first
TWO_COL_MAX_CHARS = 9000                            # small content -> 2 columns, else 3


def _css(fs: float) -> str:
    return f"""
@page {{ size: A4; margin: {PAGE_MARGIN_MM}mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "DejaVu Sans", Arial, sans-serif; font-size: {fs}pt; line-height: 1.25;
       overflow-wrap: break-word; word-wrap: break-word; }}
h1 {{ font-size: {fs * 1.5:.1f}pt; margin: 0 0 1.5mm; border-bottom: 0.6pt solid #333; }}
.cols {{ column-gap: 3mm; column-rule: 0.4pt solid #bbb; }}
.topic {{ margin: 0 0 2.5mm; }}
h2 {{ font-size: {fs * 1.2:.1f}pt; margin: 0; padding: 1px 3px; color: #fff; background: #1a5f2a; break-after: avoid; }}
h3 {{ font-size: {fs * 1.1:.1f}pt; margin: 2px 0; color: #0b3d91; break-after: avoid; }}
h4 {{ font-size: {fs * 1.08:.1f}pt; margin: 4px 0 1px; color: #1a5f2a; border-bottom: 0.4pt solid #bbb; break-after: avoid; }}
h5 {{ font-size: {fs}pt; margin: 3px 0 1px; color: #333; break-after: avoid; }}
p {{ margin: 1px 0 2px; orphans: 2; widows: 2; }}
ul, ol {{ margin: 1px 0; padding-left: 10px; }}
li {{ margin: 0; }}
pre {{ background: #f4f4f4; padding: 2px 3px; margin: 2px 0; white-space: pre-wrap; overflow-wrap: break-word;
      word-wrap: break-word; font-family: "DejaVu Sans Mono", monospace; font-size: {fs * 0.88:.2f}pt;
      line-height: 1.2; border-left: 2px solid #999; break-inside: auto; }}
code {{ font-family: "DejaVu Sans Mono", monospace; font-size: {fs * 0.9:.2f}pt; }}
img {{ display: block; max-width: 100%; height: auto; max-height: 45mm; margin: 2px auto; }}
table {{ border-collapse: collapse; width: 100%; table-layout: fixed; margin: 2px 0; font-size: {fs * 0.92:.2f}pt; }}
tr {{ break-inside: avoid; }}
td, th {{ border: 0.4pt solid #aaa; padding: 0 2px; overflow-wrap: break-word; word-wrap: break-word; vertical-align: top; }}
th {{ background: #eee; }}
.src {{ font-size: {fs * 0.75:.1f}pt; color: #777; word-break: break-all; }}
"""


def _render(date_str: str, sections: list[dict], bodies: list[str], cols: int, fs: float) -> str:
    parts = [f"<h1>Daily Study Notes - {h.escape(date_str)}</h1>"
             f"<div class='cols' style='column-count:{cols}'>"]
    for s, body in zip(sections, bodies):
        parts.append("<div class='topic'>")
        parts.append(f"<h2>{h.escape(s['topic'])}</h2><h3>{h.escape(s['subtopic'])}</h3>")
        parts.append(body or "<p><i>No content could be fetched today.</i></p>")
        if s.get("url"):
            parts.append(f"<div class='src'>{h.escape(s['url'])}</div>")
        parts.append("</div>")
    parts.append("</div>")
    return (f"<html><head><meta charset='utf-8'><style>{_css(fs)}</style></head>"
            f"<body>{''.join(parts)}</body></html>")


def build_pdf(date_str: str, sections: list[dict], out_path: str, max_pages: int = 6) -> int:
    """Full articles, never trimmed. Picks 2 columns for small content and 3 for larger
    content, then shrinks the font until the PDF fits max_pages. If even the smallest
    font doesn't fit, extra pages are added (nothing is hidden or cut)."""
    bodies = [
        full_content(s.get("html", ""),
                     embed=lambda src, base=s.get("url", ""): embed_image(src, base))
        for s in sections
    ]
    total = sum(len(re.sub(r"<[^>]+>", "", b)) for b in bodies)

    doc = None
    for fs in FONT_SIZES:
        cols = 2 if (total <= TWO_COL_MAX_CHARS and fs >= 6.2) else 3
        doc = HTML(string=_render(date_str, sections, bodies, cols, fs)).render()
        if len(doc.pages) <= max_pages:
            break
    doc.write_pdf(out_path)
    if len(doc.pages) > max_pages:
        print(f"NOTE: {len(doc.pages)} pages (target {max_pages}) - kept full content at smallest font")
    return len(doc.pages)