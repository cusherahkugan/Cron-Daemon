from weasyprint import HTML
from bundle import build_parts


CSS = """
@page {
  size: A4 landscape; margin: 24mm 22mm 17mm 22mm;
  @top-left { content: string(topic) "   \\00B7   " string(art); width: 100%; text-align: left;
              font: bold 9pt "DejaVu Sans", Arial, sans-serif; color: #1a5f2a;
              border-bottom: 0.8pt solid #1a5f2a; padding-bottom: 2mm; }
  @bottom-right { content: counter(page) " / " counter(pages);
                  font: 8.5pt "DejaVu Sans", Arial, sans-serif; color: #888; }
}
@page cover { @top-left { content: none; border: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
body { margin: 0; font-family: "DejaVu Sans", Arial, sans-serif; font-size: 12pt; line-height: 1.55;
       color: #222; overflow-wrap: break-word; word-wrap: break-word; }
.cover { page: cover; padding-top: 6mm; break-after: page; }
.cover h1 { font-size: 40pt; margin: 0 0 2mm; color: #1a5f2a; string-set: topic content(); }
.cover .date { font-size: 15pt; color: #555; margin: 0 0 9mm; }
.cover ol { font-size: 10.5pt; line-height: 1.45; padding-left: 8mm; columns: 2; column-gap: 14mm; margin: 0; }
.cover li { break-inside: avoid; margin-bottom: 1.6mm; }
.chap { break-before: page; }
.art { string-set: art content(); font-size: 24pt; line-height: 1.25; margin: 0 0 3mm; color: #111; }
.rule { border-top: 1.2pt solid #1a5f2a; margin: 0 0 8mm; }
h4 { font-size: 17pt; line-height: 1.3; color: #0b3d91; margin: 9mm 0 3mm; padding-left: 3.5mm;
     border-left: 1.6mm solid #1a5f2a; break-after: avoid; }
h5 { font-size: 14pt; line-height: 1.3; color: #333; margin: 6mm 0 2mm; break-after: avoid; }
p { margin: 0 0 3.6mm; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 4mm; padding-left: 9mm; }
li { margin: 0 0 1.8mm; }
a { color: #0b3d91; text-decoration: underline; word-break: break-all; }
pre { background: #f4f4f4; border-left: 1.4mm solid #1a5f2a; padding: 3mm 4mm; margin: 4mm 0 5mm;
      white-space: pre-wrap; overflow-wrap: break-word; font-family: "DejaVu Sans Mono", monospace;
      font-size: 9.6pt; line-height: 1.35; break-inside: auto; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 10.5pt; }
img { display: block; max-width: 100%; max-height: 105mm; width: auto; height: auto;
      margin: 5mm auto; break-inside: avoid; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; margin: 4mm 0 6mm; font-size: 10.5pt;
        line-height: 1.4; }
tr { break-inside: avoid; }
td, th { border: 0.5pt solid #aaa; padding: 1.6mm 2.4mm; vertical-align: top; overflow-wrap: break-word; }
th { background: #1a5f2a; color: #fff; text-align: left; }
tr:nth-child(even) td { background: #f7f7f7; }
.src { margin-top: 8mm; font-size: 8pt; color: #888; word-break: break-all; }
"""


def build_slides_pdf(date_str: str, topic: str, day_label: str, chapters: list[dict],
                     out_stem: str, max_pages: int = 500) -> list[tuple[str, int]]:
    """Landscape slide-style PDF(s). `out_stem` has no extension. Returns [(path, pages)]."""
    return build_parts(CSS, topic, date_str, day_label, chapters, out_stem, max_pages)