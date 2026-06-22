#!/usr/bin/env python3
"""Render DocuControl OWASP-Sicherheitsbericht (Markdown) -> PDF via WeasyPrint."""
import markdown
from weasyprint import HTML, CSS
from pathlib import Path

src = Path(__file__).resolve().parent.parent / "outputs" / "docucontrol_owasp_sicherheitsbericht.md"
dst = src.with_suffix(".pdf")

md_text = src.read_text(encoding="utf-8")

html_body = markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
)

html_doc = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>DocuControl — OWASP-Sicherheitsbericht</title>
</head>
<body>
{html_body}
</body>
</html>"""

css = CSS(string="""
@page {
    size: A4;
    margin: 2cm 2cm 2.2cm 2cm;
    @bottom-right {
        content: "Seite " counter(page) " / " counter(pages);
        font-family: "Helvetica", "Arial", sans-serif;
        font-size: 9pt;
        color: #888;
    }
    @bottom-left {
        content: "DocuControl · OWASP-Sicherheitsbericht · Juni 2026";
        font-family: "Helvetica", "Arial", sans-serif;
        font-size: 9pt;
        color: #888;
    }
}

html { font-size: 11pt; }

body {
    font-family: "Helvetica", "Arial", sans-serif;
    color: #1a1a1a;
    line-height: 1.5;
}

h1 {
    font-size: 22pt;
    color: #0d3b66;
    border-bottom: 3px solid #0d3b66;
    padding-bottom: 6pt;
    margin-top: 0;
}

h2 {
    font-size: 15pt;
    color: #0d3b66;
    margin-top: 22pt;
    border-bottom: 1px solid #c9d4e2;
    padding-bottom: 3pt;
}

h3 {
    font-size: 12pt;
    color: #2e5984;
    margin-top: 14pt;
}

p, li { font-size: 10.5pt; }

strong { color: #0d3b66; }

hr {
    border: none;
    border-top: 1px solid #d4dae3;
    margin: 18pt 0;
}

ul, ol { padding-left: 1.4em; }
li { margin-bottom: 3pt; }

table {
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0;
    font-size: 9.5pt;
}

th, td {
    border: 1px solid #c9d4e2;
    padding: 6pt 8pt;
    text-align: left;
    vertical-align: top;
}

th {
    background-color: #eaf0f7;
    color: #0d3b66;
    font-weight: 600;
}

tr:nth-child(even) td { background-color: #fafbfd; }

code {
    font-family: "DejaVu Sans Mono", "Menlo", "Consolas", monospace;
    font-size: 9.5pt;
    background-color: #f4f6f9;
    padding: 1pt 4pt;
    border-radius: 2pt;
}

em {
    color: #555;
    font-style: italic;
}

h2, h3 { page-break-after: avoid; }
table { page-break-inside: avoid; }
""")

HTML(string=html_doc).write_pdf(dst, stylesheets=[css])
print(f"OK -> {dst} ({dst.stat().st_size} bytes)")
