"""国家线统一批次导入（v0.6）。

数据来源：研招网（中国研究生招生信息网）官方发布页：
- 2024: https://yz.chsi.com.cn/kyzx/kp/202403/20240312/2293269492.html
- 2025: https://yz.chsi.com.cn/kyzx/kp/202502/20250224/2293352975.html
- 2026: https://yz.chsi.com.cn/kyzx/kp/202602/20260228/2293449093.html

口径：
1. 自 2023 年起，国家线按“学科门类 + 学科专业”公布，学硕（一级学科）与
   专业学位类别同门类同线；本批次按官方表格全表核录（含 A/B 类总分与单科）。
2. “享受少数民族照顾政策考生”与“少数民族高层次骨干人才计划”两行不属学科
   门类线，不录入本表。
3. 院校所在省在一区 → A 类线、二区 → B 类线；当前 18 所院校均在 A 区，
   B 类线仍全表核录备用。
4. 回填规则：仅更新 data_quality=official 的招录行（mock 行不动）；
   national_line 填 A/B 类总分（按院校省份），单科线与口径写 metrics。
5. 幂等：重复执行同值更新；national-lines.csv 全量重建。

用法：python scripts/ingest_national_lines.py
"""

from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DB_FILE = BACKEND / "yanduoduo_dev.db"
DATA_OFFICIAL = ROOT / "data" / "official"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE.as_posix()}"
os.environ["SQL_ECHO"] = "0"
sys.path.insert(0, str(BACKEND))

YEARS = [2024, 2025, 2026]

SOURCES = {
    2024: {
        "name": "研招网（中国研究生招生信息网）官方发布",
        "url": "https://yz.chsi.com.cn/kyzx/kp/202403/20240312/2293269492.html",
    },
    2025: {
        "name": "研招网（中国研究生招生信息网）官方发布",
        "url": "https://yz.chsi.com.cn/kyzx/kp/202502/20250224/2293352975.html",
    },
    2026: {
        "name": "研招网（中国研究生招生信息网）官方发布",
        "url": "https://yz.chsi.com.cn/kyzx/kp/202602/20260228/2293449093.html",
    },
}

# (总分, 单科满分=100, 单科满分>100)；line key -> [A 类, B 类]
# 每年全表核录（人工逐行与官方解析表比对），key 与官方行对应。
NATIONAL_LINES: dict[int, dict[str, dict]] = {
    2024: {
        "zhexue": {"gate": "哲学[01]", "sub": "各学科专业", "A": (333, 47, 71), "B": (323, 44, 66)},
        "jingjixue": {"gate": "经济学[02]", "sub": "各学科专业", "A": (338, 47, 71), "B": (328, 44, 66)},
        "faxue": {"gate": "法学[03]", "sub": "各学科专业", "A": (331, 47, 71), "B": (321, 44, 66)},
        "jiaoyu_tiyu": {"gate": "教育学[04]", "sub": "体育学[0403]、体育[0452]", "A": (313, 41, 123), "B": (303, 38, 114)},
        "jiaoyu_zhuanshu": {"gate": "教育学[04]", "sub": "教育[0451]、国际中文教育[0453]、学位授权自主审核单位自主设置的专业学位类别", "A": (350, 51, 77), "B": (340, 48, 72)},
        "jiaoyu_qita": {"gate": "教育学[04]", "sub": "其他学科专业", "A": (350, 51, 153), "B": (340, 48, 144)},
        "wenxue": {"gate": "文学[05]", "sub": "各学科专业", "A": (365, 55, 83), "B": (355, 52, 78)},
        "lishixue": {"gate": "历史学[06]", "sub": "各学科专业", "A": (345, 49, 147), "B": (335, 46, 138)},
        "lixue": {"gate": "理学[07]", "sub": "各学科专业", "A": (288, 41, 62), "B": (278, 38, 57)},
        "gongxue_zhaogu": {"gate": "工学[08]", "sub": "工学照顾专业", "A": (260, 35, 53), "B": (250, 32, 48)},
        "gongxue_qita": {"gate": "工学[08]", "sub": "其他学科专业", "A": (273, 37, 56), "B": (263, 34, 51)},
        "nongxue": {"gate": "农学[09]", "sub": "各学科专业", "A": (251, 33, 50), "B": (241, 30, 45)},
        "yixue_zhongyi": {"gate": "医学[10]", "sub": "中医学[1005]、中西医结合[1006]、中医[1057]", "A": (303, 42, 126), "B": (293, 39, 117)},
        "yixue_qita": {"gate": "医学[10]", "sub": "其他学科专业", "A": (304, 42, 126), "B": (294, 39, 117)},
        "junshixue": {"gate": "军事学[11]", "sub": "各学科专业", "A": (260, 35, 53), "B": (250, 32, 48)},
        "guanli_mba": {"gate": "管理学[12]", "sub": "工商管理[1251]、旅游管理[1254]、学位授权自主审核单位自主设置的专业学位类别", "A": (162, 39, 78), "B": (152, 34, 68)},
        "guanli_mpa": {"gate": "管理学[12]", "sub": "公共管理[1252]", "A": (173, 43, 86), "B": (163, 38, 76)},
        "guanli_kuaiji": {"gate": "管理学[12]", "sub": "会计[1253]、审计[1257]", "A": (201, 52, 104), "B": (191, 47, 94)},
        "guanli_tushu": {"gate": "管理学[12]", "sub": "图书情报[1255]", "A": (198, 51, 102), "B": (188, 46, 92)},
        "guanli_gongcheng": {"gate": "管理学[12]", "sub": "工程管理[1256]", "A": (176, 43, 86), "B": (166, 38, 76)},
        "guanli_qita": {"gate": "管理学[12]", "sub": "其他学科专业", "A": (347, 49, 74), "B": (337, 46, 69)},
        "yishuxue": {"gate": "艺术学[13]", "sub": "各学科专业", "A": (362, 40, 60), "B": (352, 37, 56)},
        "jiaochaxueke": {"gate": "交叉学科[14]", "sub": "各学科专业", "A": (275, 39, 59), "B": (265, 36, 54)},
    },
    2025: {
        "zhexue": {"gate": "哲学[01]", "sub": "各学科专业", "A": (321, 39, 59), "B": (311, 36, 54)},
        "jingjixue": {"gate": "经济学[02]", "sub": "各学科专业", "A": (323, 40, 60), "B": (313, 37, 56)},
        "faxue": {"gate": "法学[03]", "sub": "各学科专业", "A": (323, 40, 60), "B": (313, 37, 56)},
        "jiaoyu_tiyu": {"gate": "教育学[04]", "sub": "体育学[0403]、体育[0452]", "A": (304, 36, 108), "B": (294, 33, 99)},
        "jiaoyu_zhuanshu": {"gate": "教育学[04]", "sub": "教育[0451]、国际中文教育[0453]", "A": (341, 45, 68), "B": (331, 42, 63)},
        "jiaoyu_qita": {"gate": "教育学[04]", "sub": "其他学科专业", "A": (341, 45, 135), "B": (331, 42, 126)},
        "wenxue": {"gate": "文学[05]", "sub": "各学科专业", "A": (351, 47, 71), "B": (341, 44, 66)},
        "lishixue": {"gate": "历史学[06]", "sub": "各学科专业", "A": (336, 43, 129), "B": (326, 40, 120)},
        "lixue": {"gate": "理学[07]", "sub": "各学科专业", "A": (274, 34, 51), "B": (264, 31, 47)},
        "gongxue_zhaogu": {"gate": "工学[08]", "sub": "工学照顾专业", "A": (251, 33, 50), "B": (241, 30, 45)},
        "gongxue_qita": {"gate": "工学[08]", "sub": "其他学科专业", "A": (260, 34, 51), "B": (250, 31, 47)},
        "nongxue": {"gate": "农学[09]", "sub": "各学科专业", "A": (245, 33, 50), "B": (235, 30, 45)},
        "yixue_qita": {"gate": "医学[10]", "sub": "各学科专业", "A": (293, 36, 108), "B": (283, 33, 99)},
        "junshixue": {"gate": "军事学[11]", "sub": "各学科专业", "A": (260, 34, 51), "B": (250, 31, 47)},
        "guanli_mba": {"gate": "管理学[12]", "sub": "工商管理[1251]、旅游管理[1254]", "A": (151, 35, 70), "B": (141, 30, 60)},
        "guanli_mpa": {"gate": "管理学[12]", "sub": "公共管理[1252]", "A": (164, 38, 76), "B": (154, 33, 66)},
        "guanli_kuaiji": {"gate": "管理学[12]", "sub": "会计[1253]、审计[1257]", "A": (194, 48, 96), "B": (184, 43, 86)},
        "guanli_tushu": {"gate": "管理学[12]", "sub": "图书情报[1255]", "A": (191, 48, 96), "B": (181, 43, 86)},
        "guanli_gongcheng": {"gate": "管理学[12]", "sub": "工程管理[1256]", "A": (162, 38, 76), "B": (152, 33, 66)},
        "guanli_qita": {"gate": "管理学[12]", "sub": "其他学科专业", "A": (333, 41, 62), "B": (323, 38, 57)},
        "yishuxue": {"gate": "艺术学[13]", "sub": "各学科专业", "A": (351, 37, 56), "B": (341, 34, 51)},
        "jiaochaxueke": {"gate": "交叉学科[14]", "sub": "各学科专业", "A": (266, 34, 51), "B": (256, 31, 47)},
    },
    2026: {
        "zhexue": {"gate": "哲学[01]", "sub": "各学科专业", "A": (326, 41, 62), "B": (316, 38, 57)},
        "jingjixue": {"gate": "经济学[02]", "sub": "各学科专业", "A": (324, 40, 60), "B": (314, 37, 56)},
        "faxue": {"gate": "法学[03]", "sub": "各学科专业", "A": (321, 40, 60), "B": (311, 37, 56)},
        "jiaoyu_tiyu": {"gate": "教育学[04]", "sub": "体育学[0403]、体育[0452]", "A": (310, 38, 114), "B": (300, 35, 105)},
        "jiaoyu_zhuanshu": {"gate": "教育学[04]", "sub": "教育[0451]、国际中文教育[0453]", "A": (347, 48, 72), "B": (337, 45, 68)},
        "jiaoyu_qita": {"gate": "教育学[04]", "sub": "其他学科专业", "A": (347, 48, 144), "B": (337, 45, 135)},
        "wenxue": {"gate": "文学[05]", "sub": "各学科专业", "A": (354, 48, 72), "B": (344, 45, 68)},
        "lishixue": {"gate": "历史学[06]", "sub": "各学科专业", "A": (341, 45, 135), "B": (331, 42, 126)},
        "lixue": {"gate": "理学[07]", "sub": "各学科专业", "A": (275, 35, 53), "B": (265, 32, 48)},
        "gongxue_zhaogu": {"gate": "工学[08]", "sub": "工学照顾专业", "A": (251, 33, 50), "B": (241, 30, 45)},
        "gongxue_qita": {"gate": "工学[08]", "sub": "其他学科专业", "A": (264, 35, 53), "B": (254, 32, 48)},
        "nongxue": {"gate": "农学[09]", "sub": "各学科专业", "A": (240, 33, 50), "B": (230, 30, 45)},
        "yixue_qita": {"gate": "医学[10]", "sub": "各学科专业", "A": (294, 36, 108), "B": (284, 33, 99)},
        "junshixue": {"gate": "军事学[11]", "sub": "各学科专业", "A": (260, 34, 51), "B": (250, 31, 47)},
        "guanli_mba": {"gate": "管理学[12]", "sub": "工商管理[1251]", "A": (146, 35, 70), "B": (136, 30, 60)},
        "guanli_mpa": {"gate": "管理学[12]", "sub": "公共管理[1252]", "A": (168, 39, 78), "B": (158, 34, 68)},
        "guanli_kuaiji": {"gate": "管理学[12]", "sub": "会计[1253]、图书情报[1255]、审计[1257]", "A": (199, 51, 102), "B": (189, 46, 92)},
        "guanli_luyou": {"gate": "管理学[12]", "sub": "旅游管理[1254]", "A": (151, 35, 70), "B": (141, 30, 60)},
        "guanli_gongcheng": {"gate": "管理学[12]", "sub": "工程管理[1256]", "A": (166, 39, 78), "B": (156, 34, 68)},
        "guanli_qita": {"gate": "管理学[12]", "sub": "其他学科专业", "A": (332, 41, 62), "B": (322, 38, 57)},
        "yishuxue": {"gate": "艺术学[13]", "sub": "各学科专业", "A": (354, 38, 57), "B": (344, 35, 53)},
        "jiaochaxueke": {"gate": "交叉学科[14]", "sub": "各学科专业", "A": (266, 35, 53), "B": (256, 32, 48)},
    },
}

# 项目内专业 → 国家线学科专业行（学硕与专硕同门类同线）。
MAJOR_TO_LINE = {
    "081200": "gongxue_qita",
    "080200": "gongxue_qita",
    "081000": "gongxue_qita",
    "085404": "gongxue_qita",
    "085405": "gongxue_qita",
    "020204": "jingjixue",
    "025100": "jingjixue",
    "040100": "jiaoyu_qita",
    "030100": "faxue",
    "035101": "faxue",
    "035102": "faxue",
}

# 二区省区市（B 类考生）；其余均为一区（A 类）。
B_REGION_PROVINCES = {"内蒙古", "广西", "海南", "贵州", "云南", "西藏", "甘肃", "青海", "宁夏", "新疆"}


def build_national_lines_csv() -> bytes:
    rows = []
    for year in YEARS:
        source = SOURCES[year]
        for key, item in NATIONAL_LINES[year].items():
            a_total, a_low, a_high = item["A"]
            b_total, b_low, b_high = item["B"]
            rows.append(
                {
                    "年份": year,
                    "学科门类": item["gate"],
                    "学科专业（一级学科/专业学位类别）": item["sub"],
                    "A类总分": a_total,
                    "A类单科(满分=100)": a_low,
                    "A类单科(满分>100)": a_high,
                    "B类总分": b_total,
                    "B类单科(满分=100)": b_low,
                    "B类单科(满分>100)": b_high,
                    "官方URL": source["url"],
                    "核对说明": "官方发布页 HTML 表格逐行核录；原始存证见 data/official/raw/chsi/",
                }
            )
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def append_source_index() -> None:
    index_path = DATA_OFFICIAL / "source-index.csv"
    existing = set()
    if index_path.exists():
        with index_path.open(encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                existing.add((row["学校"], row["年份"]))
    with index_path.open("a", encoding="utf-8", newline="") as fh:
        for year in YEARS:
            if ("教育部（研招网发布）", str(year)) in existing:
                continue
            source = SOURCES[year]
            fh.write(
                f"教育部（研招网发布）,国家线（初试成绩基本要求）,{year},{source['url']},文字,已核对,"
                f"官方发布页全表核录；原始存证见 data/official/raw/chsi/\n"
            )


def apply_to_db() -> dict:
    """把国家线回填到全部 official 招录行（按院校所在省取 A/B 类），幂等。"""
    from app.db import SessionLocal
    from app.models import AdmissionStat, InstitutionMajor

    session = SessionLocal()
    updated = 0
    warnings: list[str] = []
    try:
        rows = (
            session.query(AdmissionStat)
            .join(InstitutionMajor, AdmissionStat.institution_major_id == InstitutionMajor.id)
            .filter(AdmissionStat.data_quality == "official")
            .all()
        )
        from app.models import Institution  # noqa: PLC0415

        for row in rows:
            im = session.get(InstitutionMajor, row.institution_major_id)
            inst = session.get(Institution, im.institution_id)
            major_code = im.major.code
            key = MAJOR_TO_LINE.get(major_code)
            if key is None:
                warnings.append(f"skip {inst.code} {major_code} {row.year}: 无类别映射")
                continue
            if str(row.year) not in {str(y) for y in YEARS} or row.year not in NATIONAL_LINES:
                warnings.append(f"skip {inst.code} {major_code} {row.year}: 年份超出本批次")
                continue
            item = NATIONAL_LINES[row.year][key]
            is_b = inst.province in B_REGION_PROVINCES
            total, low, high = item["B"] if is_b else item["A"]
            region = "B类（二区）" if is_b else "A类（一区）"
            b_total, b_low, b_high = item["B"]
            row.national_line = total
            row.metrics = {
                **(row.metrics or {}),
                "national_line_scope": (
                    f"国家线{region} {item['gate']} {item['sub']}（学硕与专硕同门类同线）；"
                    f"单科(满分=100)={low}，单科(满分>100)={high}；"
                    f"B类总分={b_total}，B类单科={b_low}/{b_high}"
                ),
            }
            # 逻辑核验：校线/院线不应低于国家线
            line = row.self_line if row.self_line is not None else row.college_line
            if line is not None and float(line) < total:
                warnings.append(
                    f"WARN {inst.code} {major_code} {row.year}: 校/院线 {line} 低于国家线 {total}"
                )
            updated += 1
        session.commit()
    finally:
        session.close()
    return {"updated": updated, "warnings": warnings}


def main() -> int:
    print(f"国家线统一批次（v0.6）：目标库 {DB_FILE}")
    if not DB_FILE.exists():
        raise SystemExit("开发库不存在，请先运行 backend/app/seed.py。")

    fact_path = DATA_OFFICIAL / "national-lines.csv"
    fact_path.write_bytes(build_national_lines_csv())
    print(f"fact sheet rebuilt: {fact_path}（3 年全表）")

    append_source_index()
    print("source index appended")

    result = apply_to_db()
    print(f"DB official rows updated: {result['updated']}")
    for w in result["warnings"]:
        print(" ", w)
    if result["warnings"]:
        print(f"WARNINGS: {len(result['warnings'])}（见上）")
    print("OK：国家线批次完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
