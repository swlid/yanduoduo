"""用 RapidOCR 读取官方表格图片，按阅读顺序输出文字，供人工核录。"""

from __future__ import annotations

import sys

from rapidocr_onnxruntime import RapidOCR


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python scripts/ocr_table_image.py <图片路径> [输出文本文件]")
        return 2
    image_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    engine = RapidOCR()
    result, _elapse = engine(image_path)
    lines: list[str] = []
    if not result:
        lines.append("NO_TEXT")
    else:
    # 按行排序：先按中心 y 分行，再按 x 排序
        items = [(box, text, score) for box, text, score in result]
        items.sort(key=lambda item: (round(sum(p[1] for p in item[0]) / 4 / 20), item[0][0][0]))
        last_row = None
        for box, text, score in items:
            row = round(sum(p[1] for p in box) / 4 / 20)
            prefix = "  " if row == last_row else ""
            lines.append(f"{prefix}{text}")
            last_row = row
    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        print(f"WROTE {out_path} ({len(lines)} lines)")
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
