"""Generate a combined Swagger UI PDF with collapsed + expanded views."""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/docs"

COLLAPSED_PDF = DOCS_DIR / "_collapsed.pdf"
EXPANDED_PDF = DOCS_DIR / "_expanded.pdf"
FINAL_PDF = DOCS_DIR / "api_documentation.pdf"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Loading {URL} ...")
        page.goto(URL, wait_until="networkidle", timeout=60_000)
        page.wait_for_selector(".opblock-summary", timeout=30_000)
        page.wait_for_timeout(2000)

        print("Printing collapsed view ...")
        page.pdf(path=str(COLLAPSED_PDF), format="A4", print_background=True)

        print("Expanding all endpoints ...")
        summaries = page.query_selector_all(".opblock-summary")
        for s in summaries:
            s.click()
            page.wait_for_timeout(50)
        page.wait_for_timeout(2000)

        print("Printing expanded view ...")
        page.pdf(path=str(EXPANDED_PDF), format="A4", print_background=True)

        browser.close()

    import subprocess

    print("Merging PDFs ...")
    subprocess.run(
        ["pdfunite", str(COLLAPSED_PDF), str(EXPANDED_PDF), str(FINAL_PDF)],
        check=True,
    )

    COLLAPSED_PDF.unlink()
    EXPANDED_PDF.unlink()

    size_kb = FINAL_PDF.stat().st_size / 1024
    print(f"Done: {FINAL_PDF} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
