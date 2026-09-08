"""真实数据批次导入 v0.3（统一脚本）。

批次内容：北京大学 / 清华大学 / 复旦大学 / 上海交通大学 / 南京大学 /
东南大学 / 华东师范大学，2024-2026 官方复试分数线（含各校实际公布口径），
共约 181 条；与既有试点 61 条同库（合计约 242 条）。

口径：只录官方公开可核实字段；官方未公布即不建行或标“暂无”。
用法：python scripts/ingest_official_batch.py
"""

from __future__ import annotations

import csv
import io
import json
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

# 自划线院校：使用 self_line（学校复试基本线）；非自划线：使用 college_line。
SELF_DRAW_CODES = {"10001", "10003", "10246", "10248", "10284", "10286", "10335"}

# 每所院校：major -> [2024, 2025, 2026 总分线]（None 表示当年官方未按该口径单列，不建行）
LINES = {
    "10001": {  # 北京大学（按学科门类/专业类别校线口径）
        "081200": [310, 300, 300],
        "080200": [310, 300, 300],
        "081000": [310, 300, 300],
        "085404": [330, 330, 320],
        "085405": [330, 330, 320],
        "020204": [375, 375, 375],
        "025100": [380, 360, 360],
        "040100": [355, 350, 350],
        "030100": [345, 345, 345],
    },
    "10003": {  # 清华大学
        "081200": [335, 325, 330],
        "080200": [335, 325, 330],
        "081000": [335, 325, 330],
        "085404": [335, 325, 330],
        "085405": [335, 325, 330],
        "020204": [350, 350, 390],
        "025100": [390, 365, 380],
        "040100": [360, 345, 375],
        "030100": [335, 323, 330],
    },
    "10246": {  # 复旦大学（2024 分一级学科，2025/2026 分学科门类/类别）
        "081200": [330, 300, 300],
        "081000": [320, 300, 300],
        "080200": [None, 300, 300],
        "085404": [300, 300, 300],
        "085405": [300, 300, 300],
        "020204": [380, 360, 360],
        "025100": [408, 365, 380],
        "040100": [370, 341, 355],
        "030100": [345, 330, 345],
    },
    "10248": {  # 上海交通大学
        "081200": [310, 300, 315],
        "080200": [310, 300, 315],
        "081000": [310, 300, 315],
        "085404": [310, 300, 315],
        "085405": [310, 300, 315],
        "020204": [375, 340, 350],
        "025100": [370, 340, 370],
        "030100": [370, 360, 345],
        "040100": [None, None, 380],
    },
    "10284": {  # 南京大学
        "081200": [305, 305, 295],
        "080200": [305, 305, 295],
        "081000": [305, 305, 295],
        "085404": [315, 315, 320],
        "085405": [315, 315, 320],
        "020204": [365, 350, 360],
        "025100": [360, 375, 325],
        "040100": [360, 345, 347],
        "030100": [340, 340, 335],
    },
    "10286": {  # 东南大学
        "081200": [310, 310, 320],
        "080200": [310, 310, 320],
        "081000": [310, 310, 320],
        "085404": [310, 310, 320],
        "085405": [310, 310, 320],
        "020204": [360, 355, 365],
        "025100": [365, 335, 380],
        "040100": [350, 341, 350],
        "030100": [375, 345, 355],
    },
    "10269": {  # 华东师范大学（分学院/专业口径，非自划线）
        "081200": [340, 325, None],
        "081000": [273, 310, None],
        "085404": [273, 260, 264],
        "085405": [273, 260, 264],
        "020204": [367, 377, 360],
        "025100": [368, 351, 357],
        "030100": [359, 338, 356],
        "040100": [376, 343, 365],
    },
}

# 培养单位：缺省为“校线口径”（自划线院校按学科门类/类别登记）；有官方分学院口径时按学院登记。
FACULTIES = {
    "10269": {
        "081200": "计算机科学与技术学院",
        "081000": "通信与电子工程学院",
        "085404": "计算机科学与技术学院",
        "085405": "软件工程学院（滴水湖国际软件学院）",
        "020204": "经济与管理学院",
        "025100": "经济与管理学院",
        "030100": "法学院",
        "040100": "教育学部",
    },
}

YEARS = [2024, 2025, 2026]

SOURCES = {
    "10001": {
        2024: {
            "name": "北京大学研究生招生办公室",
            "url": "https://admission.pku.edu.cn/docs/20240312195301489745.pdf",
        },
        2025: {
            "name": "北京大学研究生招生办公室",
            "url": "https://admission.pku.edu.cn/docs/20250312160154148797.pdf",
        },
        2026: {
            "name": "北京大学研究生招生办公室",
            "url": "https://admission.pku.edu.cn/docs/20260313100201705627.pdf",
        },
    },
    "10003": {
        2024: {
            "name": "清华大学（研招网官方存档）",
            "url": "https://yz.chsi.com.cn/kyzx/fsfsx34/202403/20240313/2293269549.html",
        },
        2025: {
            "name": "清华大学（研招网官方存档）",
            "url": "https://yz.chsi.com.cn/kyzx/fsfsx34/202503/20250312/2293356006.html",
        },
        2026: {
            "name": "清华大学研究生招生办公室",
            "url": "https://yz.tsinghua.edu.cn/info/1009/3196.htm",
        },
    },
    "10246": {
        2024: {
            "name": "复旦大学研究生院",
            "url": "https://gsao.fudan.edu.cn/28/91/c15014a665745/page.htm",
        },
        2025: {
            "name": "复旦大学研究生院",
            "url": "https://gsao.fudan.edu.cn/ff/96/c15014a720790/page.htm",
        },
        2026: {
            "name": "复旦大学研究生院",
            "url": "https://gsao.fudan.edu.cn/c8/9f/c15014a772255/page.htm",
        },
    },
    "10248": {
        2024: {
            "name": "上海交通大学研究生招生办公室",
            "url": "https://www.gs.sjtu.edu.cn/storage/gs/web/yzbcn/article/2024/04/c2662f092fb2abd1a53f37f7763e0355.pdf",
        },
        2025: {
            "name": "上海交通大学（医学院官网转载学校校级公告）",
            "url": "https://www.shsmu.edu.cn/__local/A/02/45/B1CA670395206A1F035624B155A_9723BBF0_1B5F1.pdf",
        },
        2026: {
            "name": "上海交通大学研究生招生办公室",
            "url": "https://yzb.sjtu.edu.cn/post/3503",
        },
    },
    "10284": {
        2024: {
            "name": "南京大学研究生院",
            "url": "https://yzb.nju.edu.cn/3e/ff/c47863a671487/page.htm",
        },
        2025: {
            "name": "南京大学研究生院",
            "url": "https://grawww.nju.edu.cn/6b/cb/c905a748491/page.htm",
        },
        2026: {
            "name": "南京大学研究生院",
            "url": "https://yzb.nju.edu.cn/9c/f9/c47863a826617/page.htm",
        },
    },
    "10286": {
        2024: {
            "name": "东南大学研究生院",
            "url": "https://yzb.seu.edu.cn/2024/0314/c6676a484092/page.htm",
        },
        2025: {
            "name": "东南大学研究生院",
            "url": "https://yzb.seu.edu.cn/2025/0314/c6676a521705/page.htm",
        },
        2026: {
            "name": "东南大学研究生院",
            "url": "https://yzb.seu.edu.cn/2026/0314/c6676a558100/page.psp",
        },
    },
    "10269": {
        2024: {
            "name": "华东师范大学研究生招生信息网",
            "url": "https://yjszs.ecnu.edu.cn/_upload/article/files/db/d7/3bd3f224457babca17731a7d8310/3ff99930-f6e0-488d-9ef9-aebdf36d875c.pdf",
        },
        2025: {
            "name": "华东师范大学研究生招生信息网",
            "url": "https://yjszs.ecnu.edu.cn/58/c8/c43463a678088/page.htm",
        },
        2026: {
            "name": "华东师范大学研究生招生信息网",
            "url": "https://yjszs.ecnu.edu.cn/6b/94/c43463a748436/page.htm",
        },
    },
}

NAMES = {
    "10001": "北京大学",
    "10003": "清华大学",
    "10246": "复旦大学",
    "10248": "上海交通大学",
    "10284": "南京大学",
    "10286": "东南大学",
    "10269": "华东师范大学",
}

MAJOR_NAMES = {
    "081200": "计算机科学与技术(学硕)",
    "080200": "机械工程(学硕)",
    "081000": "信息与通信工程(学硕)",
    "085404": "计算机技术(专硕)",
    "085405": "软件工程(专硕)",
    "020204": "金融学(学硕)",
    "025100": "金融(专硕)",
    "040100": "教育学(学硕)",
    "030100": "法学(学硕)",
}


def all_combos() -> list[tuple[str, str]]:
    """返回 (院校代码, 专业代码) 去重后的官方组合。"""
    combos: list[tuple[str, str]] = []
    for code, majors in LINES.items():
        for major in majors:
            pair = (code, major)
            if pair not in combos:
                combos.append(pair)
    return combos


def _csv_payload(rows: list[dict]) -> tuple[str, bytes]:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def build_institution_major_csv() -> bytes:
    rows = []
    for code, major in all_combos():
        faculty = FACULTIES.get(code, {}).get(major, "校线口径（含全校相关院系）")
        rows.append(
            {
                "institution_code": code,
                "major_code": major,
                "faculty_name": faculty,
            }
        )
    return _csv_payload(rows)


def scope_and_metrics(code: str, major: str) -> tuple[str, dict]:
    if code == "10269":
        return "school_per_major_college_line", {
            "official_line_scope": "ecnu_per_major_school_line",
            "official_line_label": "华东师大分学院专业复试线（校线）",
            "line_meaning": "达到该总分且单科不低于国家A线方可参加复试；计划口径见当年原文。",
        }
    if code in SELF_DRAW_CODES:
        return "school_basic_line_self_draw_category", {
            "official_line_scope": "school_basic_line_self_draw_category",
            "official_line_label": "自划线院校学科门类/专业类别复试基本线（学院可上浮）",
            "line_meaning": "该线为全校最低要求；具体院系/专业复试线可能更高，以当年院系公布为准。",
        }
    return "school_basic_line", {
        "official_line_scope": "school_basic_line",
        "official_line_label": "学校复试基本线",
    }


def build_admission_stat_csv() -> bytes:
    rows: list[dict] = []
    for code, majors in LINES.items():
        for major, values in majors.items():
            scope, metrics = scope_and_metrics(code, major)
            for year, line in zip(YEARS, values):
                if line is None:
                    continue
                source = SOURCES[code][year]
                row = {
                    "institution_code": code,
                    "major_code": major,
                    "year": year,
                    "self_line": line if code in SELF_DRAW_CODES else "",
                    "college_line": "" if code in SELF_DRAW_CODES else line,
                    "national_line": "",
                    "metrics": json.dumps(metrics, ensure_ascii=False),
                    "source_url": source["url"],
                    "source_name": source["name"],
                    "source_year": year,
                    "data_quality": "official",
                    "review_status": "pending",
                }
                rows.append(row)
    return _csv_payload(rows)


def expected_stat_count() -> int:
    return sum(
        1
        for majors in LINES.values()
        for values in majors.values()
        for line in values
        if line is not None
    )


def append_fact_sheets() -> None:
    """把本批事实写入 verified-lines / review-log / source-index（幂等：跳过已存在 URL+行）。"""
    verified_path = DATA_OFFICIAL / "verified-lines.csv"
    review_path = DATA_OFFICIAL / "review-log.csv"
    index_path = DATA_OFFICIAL / "source-index.csv"

    existing_verified = set()
    if verified_path.exists():
        with verified_path.open(encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                existing_verified.add((row["院校代码"], row["年份"], row["专业/学科"]))

    verified_rows = []
    review_rows = []
    for code, majors in LINES.items():
        for major, values in majors.items():
            scope, _ = scope_and_metrics(code, major)
            for year, line in zip(YEARS, values):
                if line is None:
                    continue
                key = (code, str(year), MAJOR_NAMES[major])
                if key in existing_verified:
                    continue
                note = (
                    "官方PDF/公告原文解析核录（总分线）"
                    if code in {"10001", "10246", "10248", "10284", "10286"}
                    else "官方公告原文核录（分学院/专业口径）"
                )
                if code == "10003":
                    note = "研招网官方存档核录" if year in {2024, 2025} else "清华研招官网PDF核录"
                verified_rows.append(
                    {
                        "院校代码": code,
                        "院校": NAMES[code],
                        "年份": year,
                        "口径": "分专业复试线" if code == "10269" else "学校复试基本线(学科门类/类别)",
                        "专业/学科": MAJOR_NAMES[major],
                        "总分线": line,
                        "官方URL": SOURCES[code][year]["url"],
                        "核对说明": note,
                    }
                )
                review_rows.append(
                    {
                        "院校代码": code,
                        "院校": NAMES[code],
                        "年份": year,
                        "口径": "分专业复试线" if code == "10269" else "学校复试基本线(学科门类/类别)",
                        "专业/学科": MAJOR_NAMES[major],
                        "总分线": line,
                        "官方URL": SOURCES[code][year]["url"],
                        "复核方法": note,
                        "结论": "通过",
                    }
                )

    with verified_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(verified_rows[0].keys()))
        writer.writerows(verified_rows)

    existing_seq = set()
    if review_path.exists():
        with review_path.open(encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                existing_seq.add((row["院校代码"], row["年份"], row["专业/学科"]))
    seq_start = 0
    if review_path.exists():
        with review_path.open(encoding="utf-8-sig") as fh:
            last = list(csv.DictReader(fh))
        seq_start = int(last[-1]["序号"]) if last else 0
    new_review = [
        r for r in review_rows
        if (r["院校代码"], r["年份"], r["专业/学科"]) not in existing_seq
    ]
    if new_review:
        with review_path.open("a", encoding="utf-8", newline="") as fh:
            for offset, row in enumerate(new_review, start=1):
                fh.write(f"{seq_start + offset},{row['院校代码']},{row['院校']},{row['年份']},"
                         f"{row['口径']},{row['专业/学科']},{row['总分线']},{row['官方URL']},"
                         f"{row['复核方法']},{row['结论']}\n")

    existing_index = set()
    if index_path.exists():
        with index_path.open(encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                existing_index.add((row["学校"], row["年份"]))
    with index_path.open("a", encoding="utf-8", newline="") as fh:
        for code, sources in SOURCES.items():
            for year, source in sources.items():
                if (NAMES[code], str(year)) in existing_index:
                    continue
                read_type = (
                    "PDF附件"
                    if code in {"10001", "10246", "10248", "10284", "10286"} or year in {2024, 2025, 2026}
                    and code == "10269"
                    else "文字"
                )
                if code == "10003":
                    read_type = "文字/图片(OCR)" if year in {2024, 2025} else "PDF附件"
                fh.write(
                    f"{NAMES[code]},复试基本分数线,{year},{source['url']},{read_type},已核对,"
                    f"官方原文核录；原始存证见 data/official/raw/\n"
                )


def main() -> int:
    total = expected_stat_count()
    print(f"增量导入（保留既有试点数据）：{DB_FILE}，预计新增官方招录行：{total}")
    if not DB_FILE.exists():
        raise SystemExit("开发库不存在，请先运行 backend/app/seed.py 或既有试点脚本生成基础库。")

    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.models import AdmissionStat, Institution, InstitutionMajor, Major

    official_pairs = set(all_combos())
    official_codes = set(LINES)

    with TestClient(app) as client:
        session = SessionLocal()
        try:
            targets = (
                session.query(InstitutionMajor)
                .join(Institution)
                .filter(Institution.code.in_(official_codes))
                .all()
            )
            for im in targets:
                pair = (im.institution.code, im.major.code)
                if pair in official_pairs:
                    session.delete(im)
                else:
                    im.status = "archived"
                session.commit()
        finally:
            session.close()

        resp = client.post(
            "/api/v1/admin/import",
            data={"entity_type": "institution_major"},
            files={"file": ("institution_majors.csv", build_institution_major_csv(), "text/csv")},
        )
        print("IMPORT institution_major:", resp.status_code, resp.json())
        assert resp.status_code == 200

        resp = client.post(
            "/api/v1/admin/import",
            data={"entity_type": "admission_stat"},
            files={"file": ("admission_stats.csv", build_admission_stat_csv(), "text/csv")},
        )
        body = resp.json()
        print("IMPORT admission_stat:", resp.status_code, body)
        assert resp.status_code == 200
        assert body.get("errors", []) == []
        assert body.get("created", 0) == total

        pending = client.get(
            "/api/v1/admin/admission-stats",
            params={"review_status": "pending", "page_size": 300},
        ).json()
        print("pending total:", pending["total"])
        assert pending["total"] == total
        for item in pending["items"]:
            review = client.post(
                f"/api/v1/admin/admission-stats/{item['id']}/review",
                json={"review_status": "approved", "reviewed_by": "official-batch-v03"},
            )
            assert review.status_code == 200
        print(f"REVIEW approved: {total} 条")

        # 公开接口抽查：每校 2026 至少能查回官方数据
        for keyword, expected in [
            ("北京大学", 9),
            ("清华大学", 9),
            ("复旦大学", 9),
            ("上海交通大学", 8),
            ("南京大学", 9),
            ("东南大学", 9),
            ("华东师范大学", 6),
        ]:
            resp = client.get(
                "/api/v1/institution-majors",
                params={"keyword": keyword, "year": 2026, "page_size": 100},
            ).json()
            official = [
                item for item in resp["items"]
                if item["latest_stat"] and item["latest_stat"]["data_quality"] == "official"
            ]
            print(f"{keyword} 2026 官方组合数：", len(official))
            assert len(official) >= expected

        # 测评推荐应命中多所真实数据（含新批次院校）
        assessment = client.post(
            "/api/v1/assessments",
            json={
                "undergrad_major": "计算机科学与技术",
                "target_provinces": ["北京", "上海", "江苏"],
                "estimated_total_score": 330,
                "is_cross_major": False,
                "degree_type": "学硕",
            },
        ).json()
        official_recs = [
            r for r in assessment["recommendations"]
            if r["data_refs"].get("data_quality") == "official"
        ]
        print("测评推荐数/其中官方数据：", len(assessment["recommendations"]), len(official_recs))
        assert official_recs

    append_fact_sheets()
    print("fact sheets appended")
    print("OK：真实数据批次 v0.3 导入与审核完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
