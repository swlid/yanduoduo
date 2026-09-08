"""Extract <table> rows/cells from an official HTML page for manual verification.

Usage: python scripts/extract_html_tables.py <html_path> [output_txt]
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_table = 0
        self.in_row = False
        self.in_cell = False
        self.cell_buf: list[str] = []
        self.rows: list[list[str]] = []
        self.tables: list[list[list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.in_table += 1
            self.rows = []
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.rows.append([])
        elif tag in {"td", "th"} and self.in_table:
            self.in_cell = True
            self.cell_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" or tag == "th":
            if self.in_table and self.rows and self.in_cell:
                self.rows[-1].append(" ".join("".join(self.cell_buf).split()))
            self.in_cell = False
        elif tag == "tr":
            self.in_row = False
        elif tag == "table":
            if self.in_table:
                self.tables.append(self.rows)
                self.in_table -= 1

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_buf.append(data)


def extract(path: Path) -> str:
    parser = TableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    chunks: list[str] = []
    for index, table in enumerate(parser.tables, start=1):
        if not table:
            continue
        chunks.append(f"----- TABLE {index} -----")
        for row in table:
            chunks.append(" | ".join(row))
    return "\n".join(chunks)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    html_path = Path(sys.argv[1])
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    content = extract(html_path)
    if output:
        output.write_text(content, encoding="utf-8")
        print(f"WROTE {output} ({len(content)} chars)")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
