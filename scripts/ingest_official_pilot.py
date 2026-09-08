"""真实数据试点导入（浙大 2024-2026 校线 + 杭电 2026 分专业线）。

数据来源与核验记录见 data/official/verified-lines.csv；
本脚本会重建本地开发库（Mock 由 seed 可再生），删除待升级院校-专业的旧 Mock 组合，
再通过 /admin/import CSV 接口入库、pending 审核、approved 后做公开接口抽查。

用法：在仓库根目录执行  python scripts/ingest_official_pilot.py
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

os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE.as_posix()}"
os.environ["SQL_ECHO"] = "0"
sys.path.insert(0, str(BACKEND))


# (院校代码, 专业代码, 培养单位)
OFFICIAL_COMBOS = [
    ("10335", "081200", "计算机科学与技术学院"),
    ("10335", "080200", "机械工程学院"),
    ("10335", "020204", "经济学院"),
    ("10335", "025100", "经济学院"),
    ("10335", "040100", "教育学院"),
    ("10335", "030100", "光华法学院"),
    ("10336", "081200", "计算机学院"),
    ("10336", "085404", "计算机学院"),
    ("10336", "085405", "计算机学院"),
    ("10336", "081000", "通信工程学院"),
    ("10336", "080200", "机械工程学院"),
    ("10336", "025100", "经济学院"),
    ("10701", "081200", "计算机科学与技术学院"),
    ("10701", "085404", "计算机科学与技术学院"),
    ("10701", "085405", "计算机科学与技术学院"),
    ("10280", "081200", "计算机工程与科学学院"),
    ("10280", "085404", "计算机工程与科学学院"),
    ("10280", "085405", "计算机工程与科学学院"),
    ("10280", "080200", "机电工程与自动化学院"),
    ("10280", "025100", "经济学院"),
    ("10280", "030100", "法学院"),
]


# 官方源（保持与 verified-lines.csv 一致）
ZJU_SOURCE = {
    2024: {
        "url": "http://www.grs.zju.edu.cn/yjszs/2024/0314/c28489a2890520/page.htm",
        "name": "浙江大学研究生招生处",
    },
    2025: {
        "url": "http://www.grs.zju.edu.cn/yjszs/2025/0312/c28489a3026511/page.htm",
        "name": "浙江大学研究生招生处",
    },
    2026: {
        "url": "http://www.grs.zju.edu.cn/yjszs/2026/0313/c28498a3140077/page.htm",
        "name": "浙江大学研究生招生处",
    },
}
HDU_SOURCE = {
    2024: {
        "url": "http://grs.hdu.edu.cn/2024/0327/c13498a262640/page.htm",
        "name": "杭州电子科技大学研究生院",
    },
    2025: {
        "url": "http://grs.hdu.edu.cn/2025/0326/c13498a276588/page.htm",
        "name": "杭州电子科技大学研究生院",
    },
    2026: {
        "url": "http://grs.hdu.edu.cn/2026/0324/c13270a290580/page.htm",
        "name": "杭州电子科技大学研究生院",
    }
}
XDU_SOURCE = {
    2024: {
        "url": "https://cs.xidian.edu.cn/info/1026/16334.htm",
        "name": "西安电子科技大学计算机科学与技术学院",
    },
    2025: {
        "url": "https://cs.xidian.edu.cn/info/2082/19234.htm",
        "name": "西安电子科技大学计算机科学与技术学院",
    },
    2026: {
        "url": "https://cs.xidian.edu.cn/info/2542/23764.htm",
        "name": "西安电子科技大学计算机科学与技术学院",
    },
}
SHU_SOURCE = {
    2024: {
        "url": "https://gmis.shu.edu.cn/PHP/Pub/SS_Fengshuxian.php?Year=2024",
        "name": "上海大学研究生院",
    },
    2025: {
        "url": "https://gmis.shu.edu.cn/PHP/Pub/SS_Fengshuxian.php?Year=2025",
        "name": "上海大学研究生院",
    },
    2026: {
        "url": "https://gmis.shu.edu.cn/PHP/Pub/SS_Fengshuxian.php?Year=2026",
        "name": "上海大学研究生院",
    },
}

# major_code -> {year: self_line}
ZJU_LINES = {
    "081200": {2024: 320, 2025: 300, 2026: 310},  # 工学学硕校线
    "080200": {2024: 320, 2025: 300, 2026: 310},
    "020204": {2024: 400, 2025: 370, 2026: 360},  # 经济学学硕校线
    "025100": {2024: 365, 2025: 330, 2026: 370},  # 金融专硕校线
    "040100": {2024: 370, 2025: 341, 2026: 370},  # 教育学学硕校线
    "030100": {2024: 375, 2025: 335, 2026: 365},  # 法学学硕校线
}

# 杭电分专业复试线：{major: {year: (总分, 单科100, 单科>100, 官方线标注)}}
HDU_LINES = {
    "081200": {
        2024: (300, 37, 56, "自划线"),
        2025: (285, 34, 51, "自划线"),
        2026: (325, 35, 53, "自划线"),
    },
    "085404": {
        2024: (300, 37, 56, "自划线"),
        2025: (295, 34, 51, "自划线"),
        2026: (325, 35, 53, "自划线"),
    },
    "085405": {
        2024: (290, 37, 56, "自划线"),
        2025: (295, 34, 51, "自划线"),
        2026: (290, 35, 53, "自划线"),
    },
    "081000": {
        2024: (308, 37, 56, "自划线"),
        2025: (260, 34, 51, "国家线"),
        2026: (282, 35, 53, "自划线"),
    },
    "080200": {
        2024: (273, 37, 56, "国家线"),
        2025: (260, 34, 51, "国家线"),
        2026: (264, 35, 53, "国家线"),
    },
    "025100": {
        2024: (338, 47, 71, "国家线"),
        2025: (323, 40, 60, "国家线"),
        2026: (324, 40, 60, "国家线"),
    },
}

# 西电计算机科学与技术学院（全日制 01 方向口径）
XDU_LINES = {
    "081200": {2024: 340, 2025: 330, 2026: 335},
    "085404": {2024: 315, 2025: 345, 2026: 310},
    "085405": {2024: 300, 2025: 330, 2026: 310},
}
XDU_SINGLE = (45, 70)

# 上海大学（只收录当年官方按该代码单列的专业；未单列的年份不补）
# 结构：{major: {year: (总分, 政治, 外语, 业务课1, 业务课2)}}
SHU_LINES = {
    "081200": {
        2024: (331, 50, 50, 80, 80),
        2025: (312, 45, 40, 75, 75),
        2026: (331, 45, 40, 75, 75),
    },
    "085404": {
        2025: (260, 34, 34, 51, 51),
        2026: (264, 35, 35, 53, 53),
    },
    "085405": {
        2025: (304, 45, 40, 75, 75),
        2026: (358, 45, 40, 75, 75),
    },
    "080200": {
        2024: (297, 37, 37, 56, 56),
        2025: (272, 34, 34, 51, 51),
        2026: (320, 35, 35, 53, 53),
    },
    "025100": {
        2024: (338, 47, 47, 71, 71),
        2025: (323, 40, 40, 60, 60),
        2026: (324, 40, 40, 60, 60),
    },
    "030100": {
        2024: (364, 47, 47, 71, 71),
        2025: (323, 40, 40, 60, 60),
        2026: (340, 40, 40, 60, 60),
    },
}


def _csv_payload(rows: list[dict]) -> tuple[str, bytes]:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def build_institution_major_csv() -> bytes:
    rows = [
        {
            "institution_code": code,
            "major_code": major_code,
            "faculty_name": faculty,
        }
        for code, major_code, faculty in OFFICIAL_COMBOS
    ]
    return _csv_payload(rows)


def build_admission_stat_csv() -> bytes:
    rows: list[dict] = []
    for code, major_code, _faculty in OFFICIAL_COMBOS:
        if code == "10335":
            for year, line in ZJU_LINES[major_code].items():
                source = ZJU_SOURCE[year]
                rows.append(
                    {
                        "institution_code": code,
                        "major_code": major_code,
                        "year": year,
                        "self_line": line,
                        "college_line": "",
                        "national_line": "",
                        "metrics": json.dumps(
                            {"official_line_scope": "school_basic_line_self_draw_discipline"},
                            ensure_ascii=False,
                        ),
                        "source_url": source["url"],
                        "source_name": source["name"],
                        "source_year": year,
                        "data_quality": "official",
                        "review_status": "pending",
                    }
                )
        elif code == "10336":
            for year, (line, single100, single_over, label) in HDU_LINES[major_code].items():
                source = HDU_SOURCE[year]
                rows.append(
                    {
                        "institution_code": code,
                        "major_code": major_code,
                        "year": year,
                        "self_line": "",
                        "college_line": line,
                        "national_line": "",
                        "metrics": json.dumps(
                            {
                                "official_line_scope": "school_per_major_line",
                                "official_line_label": label,
                                "single_subject": {
                                    "满分100单科": single100,
                                    "满分大于100单科": single_over,
                                },
                            },
                            ensure_ascii=False,
                        ),
                        "source_url": source["url"],
                        "source_name": source["name"],
                        "source_year": year,
                        "data_quality": "official",
                        "review_status": "pending",
                    }
                )
        elif code == "10701":
            for year, line in XDU_LINES[major_code].items():
                source = XDU_SOURCE[year]
                rows.append(
                    {
                        "institution_code": code,
                        "major_code": major_code,
                        "year": year,
                        "self_line": "",
                        "college_line": line,
                        "national_line": "",
                        "metrics": json.dumps(
                            {
                                "official_line_scope": "school_computer_college_line",
                                "direction": "01 全日制",
                                "single_subject": {
                                    "满分100单科": XDU_SINGLE[0],
                                    "满分大于100单科": XDU_SINGLE[1],
                                },
                            },
                            ensure_ascii=False,
                        ),
                        "source_url": source["url"],
                        "source_name": source["name"],
                        "source_year": year,
                        "data_quality": "official",
                        "review_status": "pending",
                    }
                )
        else:
            for year, (line, political, foreign, subj1, subj2) in SHU_LINES[major_code].items():
                source = SHU_SOURCE[year]
                rows.append(
                    {
                        "institution_code": code,
                        "major_code": major_code,
                        "year": year,
                        "self_line": "",
                        "college_line": line,
                        "national_line": "",
                        "metrics": json.dumps(
                            {
                                "official_line_scope": "school_per_major_college_line",
                                "single_subject": {
                                    "政治": political,
                                    "外语": foreign,
                                    "业务课1": subj1,
                                    "业务课2": subj2,
                                },
                            },
                            ensure_ascii=False,
                        ),
                        "source_url": source["url"],
                        "source_name": source["name"],
                        "source_year": year,
                        "data_quality": "official",
                        "review_status": "pending",
                    }
                )
    return _csv_payload(rows)


def main() -> int:
    print(f"重建开发库：{DB_FILE}")
    if DB_FILE.exists():
        DB_FILE.unlink()

    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.models import AdmissionStat, Institution, InstitutionMajor, Major

    with TestClient(app) as client:
        # 1) 清理要升级的 Mock 组合（可再生测试数据），并为同校其它 Mock 打 archived。
        session = SessionLocal()
        try:
            official_pairs = {(c, m) for c, m, _ in OFFICIAL_COMBOS}
            all_target = session.query(InstitutionMajor).join(Institution).join(Major).filter(
                Institution.code.in_(["10335", "10336", "10701", "10280"])
            ).all()
            for im in all_target:
                pair = (im.institution.code, im.major.code)
                if pair in official_pairs:
                    session.delete(im)  # 级联删除 mock 招录记录，随后由 CSV 重建官方行
                else:
                    im.status = "archived"
            session.commit()
        finally:
            session.close()

        # 2) 经管理后台 CSV 导入官方院校-专业组合
        resp = client.post(
            "/api/v1/admin/import",
            data={"entity_type": "institution_major"},
            files={"file": ("institution_majors.csv", build_institution_major_csv(), "text/csv")},
        )
        print("IMPORT institution_major:", resp.status_code, resp.json())
        assert resp.status_code == 200

        # 3) 经管理后台 CSV 导入官方招录数据（pending 待审核）
        resp = client.post(
            "/api/v1/admin/import",
            data={"entity_type": "admission_stat"},
            files={"file": ("admission_stats.csv", build_admission_stat_csv(), "text/csv")},
        )
        body = resp.json()
        print("IMPORT admission_stat:", resp.status_code, body)
        assert resp.status_code == 200
        assert body.get("errors", []) == []
        assert body.get("created", 0) == 61

        # 4) 审核全部 pending 数据
        pending = client.get(
            "/api/v1/admin/admission-stats",
            params={"review_status": "pending", "page_size": 100},
        ).json()
        assert pending["total"] == 61
        for item in pending["items"]:
            review = client.post(
                f"/api/v1/admin/admission-stats/{item['id']}/review",
                json={"review_status": "approved", "reviewed_by": "pilot-data-review"},
            )
            assert review.status_code == 200
        print("REVIEW approved: 61 条")

        # 5) 公开接口抽查
        hdu = client.get(
            "/api/v1/institution-majors",
            params={"keyword": "杭州电子科技大学", "year": 2026, "page_size": 100},
        ).json()
        official_rows = [
            item for item in hdu["items"]
            if item["latest_stat"] and item["latest_stat"]["data_quality"] == "official"
        ]
        print("HDU 2026 官方组合数：", len(official_rows))
        assert len(official_rows) >= 6

        xdu = client.get(
            "/api/v1/institution-majors",
            params={"keyword": "西安电子科技大学", "year": 2026, "page_size": 100},
        ).json()
        xdu_official = [
            item for item in xdu["items"]
            if item["latest_stat"] and item["latest_stat"]["data_quality"] == "official"
        ]
        print("XDU 2026 官方组合数：", len(xdu_official))
        assert len(xdu_official) >= 3

        zju = client.get(
            "/api/v1/institution-majors",
            params={"keyword": "浙江大学", "year": 2025, "page_size": 100},
        ).json()
        zju_official = [
            item for item in zju["items"]
            if item["latest_stat"] and item["latest_stat"]["data_quality"] == "official"
        ]
        print("ZJU 2025 官方组合数：", len(zju_official))
        assert len(zju_official) >= 5

        shu = client.get(
            "/api/v1/institution-majors",
            params={"keyword": "上海大学", "year": 2026, "page_size": 100},
        ).json()
        shu_official = [
            item for item in shu["items"]
            if item["latest_stat"] and item["latest_stat"]["data_quality"] == "official"
        ]
        print("SHU 2026 官方组合数：", len(shu_official))
        assert len(shu_official) >= 6

        # 测评推荐应能命中真实数据（浙江地区）
        assessment = client.post(
            "/api/v1/assessments",
            json={
                "undergrad_major": "软件工程",
                "target_provinces": ["浙江"],
                "estimated_total_score": 330,
                "is_cross_major": False,
                "degree_type": "不限",
            },
        )
        recs = assessment.json()["recommendations"]
        official_recs = [
            r for r in recs
            if r["data_refs"].get("data_quality") == "official"
        ]
        print("测评推荐数/其中官方数据：", len(recs), len(official_recs))
        assert assessment.status_code == 201 and official_recs

    print("OK：真实数据试点导入与审核完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
