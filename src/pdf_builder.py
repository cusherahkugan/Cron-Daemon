import html as h

from weasyprint import HTML

CSS = """
@page { size: A4; margin: 18mm; @bottom-center { content: counter(page); font-size: 9pt; } }
body { font-family: DejaVu Sans, Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; }
h1.topic { page-break-before: always; color: #1a5f2a; border-bottom: 3px solid #1a5f2a; }
h2.sub { color: #0b3d91; }
h3.art { background: #eef3ff; padding: 6px; }
pre { background: #f4f4f4; padding: 8px; white-space: pre-wrap; word-wrap: break-word;
      font-size: 9pt; border-left: 3px solid #999; }
code { font-family: DejaVu Sans Mono, monospace; }
table { border-collapse: collapse; } td, th { border: 1px solid #aaa; padding: 4px; }
.src { font-size: 8pt; color: #666; }
"""


def build_pdf(date_str: str, sections: list[dict], out_path: str) -> None:
    parts = [f"<h1>Daily Study Notes - {date_str}</h1><h3>Today's topics</h3><ul>"]
    for s in sections:
        parts.append(f"<li><b>{h.escape(s['topic'])}</b>: {h.escape(s['subtopic'])}</li>")
    parts.append("</ul>")

    for s in sections:
        parts.append(f"<h1 class='topic'>{h.escape(s['topic'])}</h1>")
        parts.append(f"<h2 class='sub'>{h.escape(s['subtopic'])}</h2>")
        if not s["articles"]:
            parts.append("<p><i>No content could be fetched today.</i></p>")
        for a in s["articles"]:
            parts.append(f"<h3 class='art'>{h.escape(a['title'])}</h3>")
            parts.append(f"<p class='src'>Source: {h.escape(a['url'])}</p>")
            parts.append(a["html"])

    doc = (
        "<html><head><meta charset='utf-8'><style>"
        + CSS
        + "</style></head><body>"
        + "".join(parts)
        + "</body></html>"
    )
    HTML(string=doc).write_pdf(out_path)