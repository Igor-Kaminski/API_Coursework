"""Convert the technical report markdown to a styled PDF."""

import re
from pathlib import Path
from playwright.sync_api import sync_playwright

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
MD_PATH = DOCS_DIR / "technical_report.md"
PDF_PATH = Path(__file__).resolve().parent.parent / "# Technical Report.pdf"


def md_to_html(md: str) -> str:
    """Minimal markdown-to-HTML without external deps."""
    html = md

    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    html = re.sub(
        r"\[([^\]]+)\]\((https?://[^\)]+)\)",
        r'<a href="\2">\1</a>',
        html,
    )
    html = re.sub(
        r"(?<![\"'>])(https?://[^\s<,]+)",
        r'<a href="\1">\1</a>',
        html,
    )

    lines = html.split("\n")
    result: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(f"<li>{stripped[2:]}</li>")
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            if stripped and not stripped.startswith("<h"):
                result.append(f"<p>{stripped}</p>")
            else:
                result.append(stripped)
    if in_list:
        result.append("</ul>")

    return "\n".join(result)


CSS = """
@page {
    size: A4;
    margin: 25mm 20mm 25mm 20mm;
    @bottom-center {
        content: "— " counter(page) " of " counter(pages) " —";
        font-size: 9pt;
        color: #888;
    }
}
body {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #1a1a1a;
    max-width: 100%;
}
h1 {
    font-size: 20pt;
    margin-bottom: 6pt;
    border-bottom: 2px solid #333;
    padding-bottom: 4pt;
}
h2 {
    font-size: 13pt;
    margin-top: 18pt;
    margin-bottom: 6pt;
    color: #2a2a2a;
}
p { margin: 6pt 0; }
code {
    background: #f0f0f0;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 10pt;
}
a { color: #1a5fb4; text-decoration: none; }
a:hover { text-decoration: underline; }
ul { margin: 4pt 0 4pt 18pt; padding: 0; }
li { margin: 2pt 0; }
"""


def main() -> None:
    md = MD_PATH.read_text(encoding="utf-8")
    body_html = md_to_html(md)
    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{body_html}</body></html>"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(full_html, wait_until="networkidle")
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            margin={"top": "25mm", "bottom": "25mm", "left": "20mm", "right": "20mm"},
        )
        browser.close()

    size_kb = PDF_PATH.stat().st_size / 1024
    print(f"Done: {PDF_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
