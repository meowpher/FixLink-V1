#!/usr/bin/env python3
"""
Export FixLink documentation from Markdown → Styled HTML → PDF
Renders tables natively, and converts Mermaid code blocks to images via mermaid.ink.
"""
import re
import sys
import base64
import urllib.parse
import markdown
from weasyprint import HTML

# ── paths ──────────────────────────────────────────────────────────────────────
SRC = "/home/taha-mustafa/.gemini/antigravity/brain/c0e4f793-2e04-4f2f-8b5e-21b85fa5ac5b/fixlink_documentation.md"
DST = "/home/taha-mustafa/Desktop/FixLink-F/FixLink_Documentation.pdf"

# ── 1. Read the markdown source ───────────────────────────────────────────────
with open(SRC, "r") as f:
    md_text = f.read()

# ── 2. Convert Mermaid fenced blocks into <img> tags via mermaid.ink ──────────
def mermaid_to_img(match):
    """Replace ```mermaid ... ``` with an <img> tag rendered by mermaid.ink."""
    raw = match.group(1).strip()
    encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
    url = f"https://mermaid.ink/img/{encoded}"
    return f'<div class="mermaid-diagram"><img src="{url}" alt="Diagram" /></div>'

md_text = re.sub(
    r"```mermaid\s*\n(.*?)```",
    mermaid_to_img,
    md_text,
    flags=re.DOTALL,
)

# ── 3. Convert Markdown → HTML ───────────────────────────────────────────────
body_html = markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br"],
    extension_configs={"codehilite": {"guess_lang": False, "css_class": "code"}},
)

# ── 4. Wrap in a complete HTML document with print-optimised CSS ─────────────
full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
/* ── Page setup ──────────────────────────────────────────────── */
@page {{
    size: A4;
    margin: 22mm 18mm 22mm 18mm;

    @top-center {{
        content: "FixLink — Project Documentation";
        font-size: 8pt;
        color: #999;
        font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
    @bottom-center {{
        content: "Page " counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #999;
        font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif;
    }}
}}

/* ── Typography ──────────────────────────────────────────────── */
body {{
    font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #1e293b;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

/* ── Headings ────────────────────────────────────────────────── */
h1 {{
    font-size: 26pt;
    font-weight: 800;
    color: #0b4d8c;
    margin-top: 0;
    margin-bottom: 6pt;
    padding-bottom: 10pt;
    border-bottom: 3pt solid #0b4d8c;
    page-break-after: avoid;
}}

h2 {{
    font-size: 17pt;
    font-weight: 700;
    color: #0b4d8c;
    margin-top: 28pt;
    margin-bottom: 8pt;
    padding-bottom: 5pt;
    border-bottom: 1.5pt solid #cfdbe8;
    page-break-after: avoid;
}}

h3 {{
    font-size: 13pt;
    font-weight: 700;
    color: #1e3a5f;
    margin-top: 20pt;
    margin-bottom: 6pt;
    page-break-after: avoid;
}}

h4 {{
    font-size: 11.5pt;
    font-weight: 700;
    color: #334155;
    margin-top: 16pt;
    margin-bottom: 4pt;
    page-break-after: avoid;
}}

/* ── Paragraphs & lists ──────────────────────────────────────── */
p {{ margin: 6pt 0; }}

ul, ol {{
    margin: 4pt 0 4pt 16pt;
    padding-left: 10pt;
}}
li {{ margin-bottom: 3pt; }}

/* ── Blockquotes (used for the intro callout) ────────────────── */
blockquote {{
    background: #f0f5fc;
    border-left: 4pt solid #0b4d8c;
    margin: 14pt 0;
    padding: 12pt 16pt;
    border-radius: 4pt;
    color: #334155;
}}
blockquote p {{ margin: 3pt 0; }}
blockquote strong {{ color: #0b4d8c; }}

/* ── Tables ──────────────────────────────────────────────────── */
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0 14pt 0;
    font-size: 9.5pt;
    page-break-inside: auto;
}}
thead {{
    display: table-header-group;   /* repeat header on page breaks */
}}
tr {{
    page-break-inside: avoid;
    page-break-after: auto;
}}
th {{
    background-color: #0b4d8c;
    color: #ffffff;
    font-weight: 700;
    text-align: left;
    padding: 7pt 10pt;
    border: 1pt solid #0b4d8c;
}}
td {{
    padding: 6pt 10pt;
    border: 1pt solid #d1d9e0;
    vertical-align: top;
}}
tr:nth-child(even) td {{
    background-color: #f8fafc;
}}
tr:hover td {{
    background-color: #eef3f9;
}}

/* ── Code blocks ─────────────────────────────────────────────── */
code {{
    font-family: 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
    font-size: 9pt;
    background: #f1f5f9;
    padding: 1.5pt 5pt;
    border-radius: 3pt;
    color: #c8102e;
}}
pre {{
    background: #1e293b;
    color: #e2e8f0;
    padding: 14pt 16pt;
    border-radius: 6pt;
    overflow-x: auto;
    font-size: 8.5pt;
    line-height: 1.55;
    margin: 10pt 0;
    page-break-inside: avoid;
}}
pre code {{
    background: transparent;
    color: inherit;
    padding: 0;
    font-size: inherit;
}}

/* ── Mermaid diagrams ────────────────────────────────────────── */
.mermaid-diagram {{
    text-align: center;
    margin: 16pt 0;
    page-break-inside: avoid;
}}
.mermaid-diagram img {{
    max-width: 100%;
    height: auto;
    border: 1pt solid #e2e8f0;
    border-radius: 6pt;
    padding: 8pt;
    background: #ffffff;
}}

/* ── Horizontal rules ────────────────────────────────────────── */
hr {{
    border: none;
    border-top: 1.5pt solid #cbd5e1;
    margin: 20pt 0;
}}

/* ── Strong / emphasis ───────────────────────────────────────── */
strong {{ color: #0f172a; }}

/* ── Links ───────────────────────────────────────────────────── */
a {{
    color: #0b4d8c;
    text-decoration: none;
}}

/* ── Alerts / callouts > [!NOTE] etc ─────────────────────────── */
.admonition {{
    padding: 10pt 14pt;
    margin: 12pt 0;
    border-radius: 4pt;
    border-left: 4pt solid #0b4d8c;
    background: #f0f5fc;
}}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

# ── 5. Render to PDF ──────────────────────────────────────────────────────────
print(f"Rendering PDF → {DST}")
HTML(string=full_html).write_pdf(DST)
print(f"✅ PDF successfully exported to:\n   {DST}")
