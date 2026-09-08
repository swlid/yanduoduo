"""Extract text/tables from a PDF for manual verification (official 分数线 files).

Usage: python scripts/parse_pdf.py <pdf_path> [output_txt]
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError as exc:  # pragma: no cover
    raise SystemExit("缺少 pdfplumber，请先安装：pip install pdfplumber") from exc


def extract(path: Path) -> str:
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            chunks.append(f"===== PAGE {page_index} =====")
            text = page.extract_text() or ""
            chunks.append(text)
            tables = page.extract_tables()
            for table_index, table in enumerate(tables, start=1):
                chunks.append(f"----- TABLE {table_index} -----")
                for row in table:
                    cells = ["" if c is None else str(c).replace("\n", " ") for c in row]
                    chunks.append(" | ".join(cells))
    return "\n".join(chunks)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pdf_path = Path(sys.argv[1])
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if not pdf_path.exists():
        print(f"文件不存在：{pdf_path}")
        return 1
    content = extract(pdf_path)
    if output:
        output.write_text(content, encoding="utf-8")
        print(f"已写入：{output}")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
