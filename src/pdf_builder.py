import html as h

from weasyprint import HTML

from condense import condense
from scrape import embed_image

CSS = """
@page { size: A4; margin: 8mm; @bottom-center { content: counter(page); font-size: 6pt; color: #666; } }
body { font-family: DejaVu Sans, Arial, sans-serif; font-size: 6.8pt; line-height: 1.25; }
h1 { font-size: 10pt; margin: 0 0 2mm; border-bottom: 1px solid #333; }
.topic { margin-bottom: 2.5mm; }
h2 { font-size: 8pt; margin: 0; padding: 1px 3px; color: #fff; background: #1a5f2a; break-after: avoid; }
h3 { font-size: 7pt; margin: 1px 0; color: #0b3d91; break-after: avoid; }
h4 { font-size: 6.8pt; margin: 2px 0 0; color: #333; break-after: avoid; }
p { margin: 1px 0; } ul { margin: 1px 0; padding-left: 10px; } li { margin: 0; }
pre { background: #f4f4f4; padding: 2px 3px; margin: 2px 0; white-space: pre-wrap; word-wrap: break-word;
      font-size: 5.8pt; line-height: 1.2; border-left: 2px solid #999; }
img { display: block; max-width: 100%; max-height: 38mm; margin: 2px auto; }
.src { font-size: 5pt; color: #777; word-break: break-all; }
.cols { column-count: 2; column-gap: 5mm; }
"""


def _render(date_str: str, sections: list[dict], budget: int, max_images: int) -> str:
    parts = [f"<h1>Daily Study Notes - {h.escape(date_str)}</h1><div class='cols'>"]
    for s in sections:
        parts.append("<div class='topic'>")
        parts.append(f"<h2>{h.escape(s['topic'])}</h2><h3>{h.escape(s['subtopic'])}</h3>")
        body = condense(
            s.get("html", ""), budget, max_images,
            embed=lambda src, base=s.get("url", ""): embed_image(src, base),
        )
        parts.append(body or "<p><i>No content could be fetched today.</i></p>")
        if s.get("url"):
            parts.append(f"<div class='src'>{h.escape(s['url'])}</div>")
        parts.append("</div>")
    parts.append("</div>")
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(parts)}</body></html>"


def build_pdf(date_str: str, sections: list[dict], out_path: str, max_pages: int = 6) -> int:
    """Render, and if over max_pages shrink the per-topic text budget until it fits."""
    budget, max_images = 3000, 2
    while True:
        doc = HTML(string=_render(date_str, sections, budget, max_images)).render()
        if len(doc.pages) <= max_pages or budget <= 250:
            break
        budget = int(budget * 0.8)
        if budget < 1200:
            max_images = 1
        if budget < 600:
            max_images = 0
    doc.write_pdf(out_path)
    if len(doc.pages) > max_pages:
        print(f"WARNING: {len(doc.pages)} pages, above max_pages={max_pages}")
    return len(doc.pages)