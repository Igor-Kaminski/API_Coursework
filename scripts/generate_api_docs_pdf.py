from pathlib import Path
from textwrap import wrap


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 50
TOP_MARGIN = 750
LINE_HEIGHT = 14
MAX_LINE_WIDTH = 92
MAX_LINES_PER_PAGE = 48


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def paginate_lines(lines: list[str]) -> list[list[str]]:
    pages: list[list[str]] = []
    current_page: list[str] = []

    for raw_line in lines:
        wrapped = wrap(raw_line, width=MAX_LINE_WIDTH) or [""]
        for line in wrapped:
            if len(current_page) >= MAX_LINES_PER_PAGE:
                pages.append(current_page)
                current_page = []
            current_page.append(line)

    if current_page:
        pages.append(current_page)
    return pages


def build_stream(lines: list[str]) -> str:
    content = ["BT", "/F1 10 Tf", f"{LEFT_MARGIN} {TOP_MARGIN} Td", f"{LINE_HEIGHT} TL"]
    for line in lines:
        content.append(f"({escape_pdf_text(line)}) Tj")
        content.append("T*")
    content.append("ET")
    return "\n".join(content)


def generate_pdf(markdown_path: Path, output_path: Path) -> None:
    source_text = markdown_path.read_text(encoding="utf-8")
    pages = paginate_lines(source_text.splitlines())
    objects: list[str] = []

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")

    page_object_numbers = [4 + index * 2 for index in range(len(pages))]
    page_references = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects.append(f"<< /Type /Pages /Count {len(pages)} /Kids [{page_references}] >>")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for index, page_lines in enumerate(pages):
        page_object = 4 + index * 2
        content_object = page_object + 1
        stream = build_stream(page_lines)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object} 0 R >>"
        )
        objects.append(f"<< /Length {len(stream.encode('utf-8'))} >>\nstream\n{stream}\nendstream")

    output = ["%PDF-1.4"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk.encode("utf-8")) + 1 for chunk in output))
        output.append(f"{index} 0 obj\n{obj}\nendobj")

    xref_offset = sum(len(chunk.encode("utf-8")) + 1 for chunk in output)
    xref_lines = ["xref", f"0 {len(objects) + 1}", "0000000000 65535 f "]
    for offset in offsets[1:]:
        xref_lines.append(f"{offset:010d} 00000 n ")

    trailer = [
        "trailer",
        f"<< /Size {len(objects) + 1} /Root 1 0 R >>",
        "startxref",
        str(xref_offset),
        "%%EOF",
    ]

    output.extend(xref_lines)
    output.extend(trailer)
    output_path.write_bytes(("\n".join(output) + "\n").encode("utf-8"))


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    markdown = project_root / "docs" / "api-documentation.md"
    pdf = project_root / "docs" / "api-documentation.pdf"
    generate_pdf(markdown, pdf)
    print(f"Generated {pdf}")
