from weasyprint import HTML
from bundle import build_parts


CSS = """
@page {
  size: A4; margin: 18mm 16mm 16mm 16mm;
  @top-left { content: string(topic) "  \\00B7  " string(art); width: 100%;
              font: bold 8pt "DejaVu Sans", Arial, sans-serif; color: #1a5f2a;
              border-bottom: 0.6pt solid #1a5f2a; padding-bottom: 1.5mm; }
  @bottom-right { content: counter(page) " / " counter(pages);
                  font: 8pt "DejaVu Sans", Arial, sans-serif; color: #888; }
}
@page cover { @top-left { content: none; border: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
body { margin: 0; font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.5;
       color: #222; overflow-wrap: break-word; word-wrap: break-word; }
.cover { page: cover; break-after: page; }
.cover h1 { font-size: 30pt; margin: 0 0 2mm; color: #1a5f2a; string-set: topic content(); }
.cover .date { font-size: 12pt; color: #555; margin: 0 0 8mm; }
.cover ol { font-size: 9.5pt; line-height: 1.45; padding-left: 7mm; margin: 0; }
.cover li { margin-bottom: 1mm; }
.art { string-set: art content(); font-size: 16pt; line-height: 1.3; margin: 10mm 0 1mm; color: #111;
       break-after: avoid; }
.rule { border-top: 1.2pt solid #1a5f2a; margin: 0 0 4mm; }
h4 { font-size: 13pt; color: #0b3d91; margin: 6mm 0 2mm; padding-left: 3mm;
     border-left: 1.2mm solid #1a5f2a; break-after: avoid; }
h5 { font-size: 11.5pt; color: #333; margin: 4mm 0 1.5mm; break-after: avoid; }
p { margin: 0 0 2.6mm; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 3mm; padding-left: 7mm; }
li { margin: 0 0 1.2mm; }
a { color: #0b3d91; text-decoration: underline; word-break: break-all; }
pre { background: #f4f4f4; border-left: 1.2mm solid #1a5f2a; padding: 2.5mm 3mm; margin: 3mm 0 4mm;
      white-space: pre-wrap; overflow-wrap: break-word; font-family: "DejaVu Sans Mono", monospace;
      font-size: 8.6pt; line-height: 1.35; break-inside: auto; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; }
img { display: block; max-width: 100%; max-height: 110mm; width: auto; height: auto;
      margin: 3mm auto; break-inside: avoid; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; margin: 3mm 0 4mm; font-size: 9pt; }
tr { break-inside: avoid; }
td, th { border: 0.5pt solid #aaa; padding: 1.2mm 2mm; vertical-align: top; overflow-wrap: break-word; }
th { background: #1a5f2a; color: #fff; text-align: left; }
.src { margin-top: 4mm; font-size: 7pt; color: #888; word-break: break-all; }
"""


def build_pdf(date_str: str, topic: str, day_label: str, chapters: list[dict],
              out_stem: str, max_pages: int = 500) -> list[tuple[str, int]]:
    """A4 PDF(s). `out_stem` has no extension. Returns [(path, pages)]."""
    return build_parts(CSS, topic, date_str, day_label, chapters, out_stem, max_pages)