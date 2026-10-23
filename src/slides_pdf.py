"""Slide-style PDF: landscape A4 pages that look like lecture slides but keep ALL of the
scraped content (every heading, paragraph, list, code block, table and image).

Nothing is condensed or dropped: long topics simply run onto more pages. Each topic starts
on a fresh page, with a running header (topic - subtopic) and a page counter."""
import html as h

from weasyprint import HTML

from condense import full_content
from scrape import embed_image

CSS = """
@page {
  size: A4 landscape;
  margin: 24mm 22mm 17mm 22mm;
  @top-left {
    content: string(topic) "   \\00B7   " string(sub);
    width: 100%;
    text-align: left;
    font: bold 9pt "DejaVu Sans", Arial, sans-serif;
    color: #1a5f2a;
    border-bottom: 0.8pt solid #1a5f2a;
    padding-bottom: 2mm;
  }
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font: 8.5pt "DejaVu Sans", Arial, sans-serif;
    color: #888;
  }
}
@page cover {
  @top-left { content: none; border: none; }
  @bottom-right { content: none; }
}
* { box-sizing: border-box; }
body { margin: 0; font-family: "DejaVu Sans", Arial, sans-serif; font-size: 12pt; line-height: 1.55;
       color: #222; overflow-wrap: break-word; word-wrap: break-word; }

.cover { page: cover; padding-top: 6mm; }
.cover h1 { font-size: 36pt; margin: 0 0 2mm; color: #1a5f2a; }
.cover .date { font-size: 16pt; color: #555; margin: 0 0 9mm; }
.cover ol { font-size: 11.5pt; line-height: 1.5; padding-left: 8mm; columns: 2; column-gap: 14mm; margin: 0; }
.cover li { break-inside: avoid; margin-bottom: 2.4mm; }
.cover b { color: #1a5f2a; }

.topic { break-before: page; }
.tname { string-set: topic content(); font-size: 11pt; letter-spacing: 1.5pt; text-transform: uppercase;
         color: #1a5f2a; margin: 0 0 1.5mm; }
.sub { string-set: sub content(); font-size: 24pt; line-height: 1.25; margin: 0 0 3mm; color: #111; }
.rule { border-top: 1.2pt solid #1a5f2a; margin: 0 0 8mm; }

h4 { font-size: 17pt; line-height: 1.3; color: #0b3d91; margin: 9mm 0 3mm; padding-left: 3.5mm;
     border-left: 1.6mm solid #1a5f2a; break-after: avoid; }
h5 { font-size: 14pt; line-height: 1.3; color: #333; margin: 6mm 0 2mm; break-after: avoid; }
p { margin: 0 0 3.6mm; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 4mm; padding-left: 9mm; }
li { margin: 0 0 1.8mm; }
pre { background: #f4f4f4; border-left: 1.4mm solid #1a5f2a; padding: 3mm 4mm; margin: 4mm 0 5mm;
      white-space: pre-wrap; overflow-wrap: break-word; word-wrap: break-word;
      font-family: "DejaVu Sans Mono", monospace; font-size: 9.6pt; line-height: 1.35; break-inside: auto; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 10.5pt; }
img { display: block; max-width: 100%; max-height: 105mm; width: auto; height: auto;
      margin: 5mm auto; break-inside: avoid; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; margin: 4mm 0 6mm; font-size: 10.5pt;
        line-height: 1.4; }
tr { break-inside: avoid; }
td, th { border: 0.5pt solid #aaa; padding: 1.6mm 2.4mm; vertical-align: top; overflow-wrap: break-word;
         word-wrap: break-word; }
th { background: #1a5f2a; color: #fff; text-align: left; }
tr:nth-child(even) td { background: #f7f7f7; }
.src { margin-top: 8mm; font-size: 8pt; color: #888; word-break: break-all; }
"""


def _render(date_str: str, sections: list[dict], bodies: list[str]) -> str:
    agenda = "".join(
        f"<li><b>{h.escape(s['topic'])}</b> &nbsp;{h.escape(s['subtopic'])}</li>" for s in sections)
    parts = [f"<section class='cover'><h1>Daily Study Notes</h1>"
             f"<p class='date'>{h.escape(date_str)}</p><ol>{agenda}</ol></section>"]
    for s, body in zip(sections, bodies):
        parts.append("<section class='topic'>")
        parts.append(f"<h2 class='tname'>{h.escape(s['topic'])}</h2>"
                     f"<h3 class='sub'>{h.escape(s['subtopic'])}</h3><div class='rule'></div>")
        parts.append(body or "<p><i>No content could be fetched today.</i></p>")
        if s.get("url"):
            parts.append(f"<div class='src'>{h.escape(s['url'])}</div>")
        parts.append("</section>")
    return (f"<html><head><meta charset='utf-8'><style>{CSS}</style></head>"
            f"<body>{''.join(parts)}</body></html>")


def build_slides_pdf(date_str: str, sections: list[dict], out_path: str) -> int:
    """Write the slide-style PDF (landscape A4, full content) and return its page count."""
    bodies = [
        full_content(s.get("html", ""),
                     embed=lambda src, base=s.get("url", ""): embed_image(src, base))
        for s in sections
    ]
    doc = HTML(string=_render(date_str, sections, bodies)).render()
    doc.write_pdf(out_path)
    return len(doc.pages)