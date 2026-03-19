from pathlib import Path


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 50
TOP_MARGIN = 780
LINE_HEIGHT = 14
FONT_SIZE = 11
MAX_CHARS = 88


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_line(line: str, width: int = MAX_CHARS) -> list[str]:
    if not line:
        return [""]

    words = line.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def build_page_content(lines: list[str]) -> str:
    commands = ["BT", f"/F1 {FONT_SIZE} Tf"]
    y_position = TOP_MARGIN
    for line in lines:
        commands.append(f"1 0 0 1 {LEFT_MARGIN} {y_position} Tm ({escape_pdf_text(line)}) Tj")
        y_position -= LINE_HEIGHT
    commands.append("ET")
    return "\n".join(commands)


def paginate(lines: list[str], lines_per_page: int = 48) -> list[list[str]]:
    pages: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        wrapped = wrap_line(line)
        for wrapped_line in wrapped:
            if len(current) >= lines_per_page:
                pages.append(current)
                current = []
            current.append(wrapped_line)

    if current:
        pages.append(current)
    return pages


def build_pdf(page_contents: list[str]) -> bytes:
    objects: list[str] = []

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{index} 0 R" for index in range(3, 3 + len(page_contents) * 2, 2))
    objects.append(f"<< /Type /Pages /Count {len(page_contents)} /Kids [{kids}] >>")

    font_object_id = 3 + len(page_contents) * 2

    for index, content in enumerate(page_contents):
        page_object_id = 3 + index * 2
        content_object_id = page_object_id + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> /Contents {content_object_id} 0 R >>"
        )
        objects.append(f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream")

    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = "%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf.encode("latin-1")))
        pdf += f"{index} 0 obj\n{obj}\nendobj\n"

    xref_offset = len(pdf.encode("latin-1"))
    pdf += f"xref\n0 {len(objects) + 1}\n"
    pdf += "0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += (
        "trailer\n"
        f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        "startxref\n"
        f"{xref_offset}\n"
        "%%EOF\n"
    )
    return pdf.encode("latin-1")


def main() -> None:
    source_path = Path("docs/api_documentation.md")
    output_path = Path("docs/api_documentation.pdf")

    lines = source_path.read_text(encoding="utf-8").splitlines()
    page_contents = [build_page_content(page) for page in paginate(lines)]
    output_path.write_bytes(build_pdf(page_contents))
    print(f"generated {output_path}")


if __name__ == "__main__":
    main()
