"""导入用户投递的全国招生单位名单（885 所），扩充院校库。

数据来源：`data/imports/extracted/02_招生单位885所.csv`（用户投递，字段含研招网 schId、
省份、主管部门、双一流/研究生院/自划线标记、研招网学校页链接），层次映射见
`data/imports/extracted/ref_levels.json`。

口径与约定：
1. 已有院校（20 所）按名称匹配，保留原有 5 位单位代码、城市与院校类型，只补充
   自划线标记、研招网链接与标签。
2. 新增院校的 `code` 使用研招网 schId（研招网学校页 URL 中的编号），因为本批次不含
   5 位单位代码；`code_type=yz_sch_id` 写入 tags，待取得单位代码后再覆盖。
3. 本批次不提供城市与院校类型，按用户确认：`category` 记「暂无」，`city` 同样记「暂无」。
4. 幂等：重复执行只做更新，不重复新增。

用法：python scripts/ingest_institutions.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DB_FILE = BACKEND / "yanduoduo_dev.db"
CSV_885 = ROOT / "data" / "imports" / "extracted" / "02_招生单位885所.csv"
LEVELS_JSON = ROOT / "data" / "imports" / "extracted" / "ref_levels.json"

PLACEHOLDER = "暂无"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE.as_posix()}"
os.environ["SQL_ECHO"] = "0"
sys.path.insert(0, str(BACKEND))


def main() -> int:
    if not DB_FILE.exists():
        raise SystemExit("开发库不存在，请先运行 backend/app/seed.py。")

    rows = list(csv.DictReader(CSV_885.open(encoding="utf-8-sig")))
    levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))

    from app.db import SessionLocal
    from app.models import Institution

    session = SessionLocal()
    created = updated = unchanged = 0
    level_changes: list[str] = []
    self_draw_added: list[str] = []
    try:
        existing = {inst.name: inst for inst in session.query(Institution).all()}
        for row in rows:
            name = row["name"].strip()
            sch_id = str(row["sch_id"]).strip()
            province = row["province"].strip()
            is_self_draw = row["is_self_line"].strip() == "1"
            level = levels.get(name, "普通")
            tags = [
                {
                    "yz_sch_id": sch_id,
                    "department": row.get("department", "").strip(),
                    "is_double_first": row["is_double_first"].strip() == "1",
                    "has_graduate_school": row["has_graduate_school"].strip() == "1",
                    "code_type": "yz_sch_id" if name not in existing else "unit_code",
                }
            ]

            inst = existing.get(name)
            if inst is None:
                inst = Institution(
                    code=sch_id,
                    name=name,
                    short_name="",
                    province=province,
                    city=PLACEHOLDER,
                    level=level,
                    category=PLACEHOLDER,
                    is_self_draw=is_self_draw,
                    official_url=row.get("source_url") or None,
                    tags=tags,
                    status="published",
                )
                session.add(inst)
                existing[name] = inst
                created += 1
                continue

            changed = False
            if inst.level != level:
                level_changes.append(f"{name}: {inst.level} -> {level}")
                inst.level = level
                changed = True
            if inst.is_self_draw != is_self_draw:
                if is_self_draw:
                    self_draw_added.append(name)
                inst.is_self_draw = is_self_draw
                changed = True
            if not inst.official_url and row.get("source_url"):
                inst.official_url = row["source_url"]
                changed = True
            if not inst.tags:
                inst.tags = tags
                changed = True
            if changed:
                updated += 1
            else:
                unchanged += 1

        session.commit()
        total = session.query(Institution).count()
        self_draw_total = (
            session.query(Institution).filter(Institution.is_self_draw.is_(True)).count()
        )
    finally:
        session.close()

    print(f"输入行数 {len(rows)}：新增 {created}、更新 {updated}、无变化 {unchanged}")
    print(f"库内院校总数 {total}，其中自划线 {self_draw_total}")
    if level_changes:
        print("层次调整：")
        for item in level_changes:
            print("  " + item)
    if self_draw_added:
        print("新增自划线标记：", "、".join(self_draw_added))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
