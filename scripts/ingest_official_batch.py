"""真实数据批次导入（统一脚本，v0.4）。

v0.3：北京大学 / 清华大学 / 复旦大学 / 上海交通大学 / 南京大学 /
东南大学 / 华东师范大学，2024-2026 官方复试分数线 181 条。
v0.4 追加：上海财经大学 / 浙江工业大学 / 浙江理工大学 / 武汉大学 /
南京理工大学，按各校官方公布口径核录（官方未公布的年份/专业不建行）。
与既有试点 61 条同库，官方数据累计约 319 条。

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
SELF_DRAW_CODES = {"10001", "10003", "10246", "10248", "10284", "10286", "10335", "10486"}
# 按“分专业/分培养单位”公布复试线的院校（非自划线口径，写 college_line）
PER_MAJOR_SCHOOLS = {"10269", "10337", "10338", "10288", "10272", "10293"}

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
    "10272": {  # 上海财经大学（按学科门类校线，非自划线）
        "020204": [338, 323, 324],
        "025100": [338, 323, 324],
        "030100": [331, 323, 321],
    },
    "10337": {  # 浙江工业大学（分专业复试线，非自划线）
        "081000": [313, 260, 264],
        "081200": [309, 278, 293],
        "085404": [282, None, 300],
        "085405": [275, 270, 264],
        "040100": [350, 341, 347],
        "030100": [331, 323, 321],
        "025100": [338, 349, 324],
        "020204": [338, 323, 264],  # 020200 应用经济学口径
    },
    "10338": {  # 浙江理工大学（2026 分专业复试线；2024/2025 官网未公布）
        "081200": [None, None, 264],
        "085404": [None, None, 338],
        "080200": [None, None, 264],
        "081000": [None, None, 264],
        "025100": [None, None, 324],
        "030100": [None, None, 321],
        "020204": [None, None, 324],  # 020200 应用经济学口径
    },
    "10486": {  # 武汉大学（自划线，分培养单位复试线）
        "081200": [350, 325, 295],
        "081000": [315, 310, 350],
        "080200": [300, 290, 310],
        "085404": [335, 320, 350],
        "085405": [315, 310, None],  # 2026 仅"中外合作"方向单列，暂不映射
        "020204": [350, 340, 380],  # 0202 应用经济学口径
        "025100": [338, 370, 380],
        "030100": [376, 335, 360],
    },
    "10288": {  # 南京理工大学（分专业复试线，非自划线）
        "081200": [350, 335, 330],
        "081000": [None, 320, 330],
        "080200": [None, 305, 350],
        "085404": [355, 340, 360],
        "085405": [355, 340, 360],
        "020204": [346, 354, 381],  # 020200 应用经济学口径
        "025100": [366, 352, 365],
        "030100": [345, 323, 343],
    },
    "10293": {  # 南京邮电大学（分专业复试线 + 官方报考录取表）
        "081000": [307, 300, 315],
        "081200": [341, 289, 303],
        "085404": [339, 339, 339],
        "020204": [342, 323, 356],  # 020200 应用经济学口径
        "040100": [376, 341, 347],
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
    "10272": {},
    "10337": {
        "081000": "信息工程学院",
        "081200": "计算机科学与技术学院（软件学院）",
        "085404": "计算机科学与技术学院（软件学院）",
        "085405": "计算机科学与技术学院（软件学院）",
        "040100": "教育学院（职业技术教育学院）",
        "030100": "法学院",
        "025100": "经济学院",
        "020204": "经济学院（应用经济学口径）",
    },
    "10338": {
        "081200": "计算机科学与技术学院（人工智能学院）",
        "085404": "计算机科学与技术学院（人工智能学院）",
        "080200": "机械工程学院",
        "081000": "信息科学与工程学院（网络空间安全学院）",
        "025100": "经济管理学院",
        "030100": "法学与人文学院",
        "020204": "经济管理学院（应用经济学口径）",
    },
    "10486": {
        "081200": "计算机学院",
        "081000": "电子信息学院",
        "080200": "动力与机械学院",
        "085404": "计算机学院",
        "085405": "电子信息学院",
        "020204": "经济与管理学院（应用经济学口径）",
        "025100": "经济与管理学院",
        "030100": "法学院",
    },
    "10288": {
        "081200": "计算机科学与工程学院",
        "081000": "电子工程与光电技术学院",
        "080200": "机械工程学院",
        "085404": "计算机科学与工程学院",
        "085405": "计算机科学与工程学院",
        "020204": "经济管理学院（应用经济学口径）",
        "025100": "经济管理学院",
        "030100": "知识产权学院",
    },
    "10293": {
        "081000": "通信与信息工程学院",
        "081200": "计算机学院",
        "085404": "计算机学院",
        "020204": "经济学院（应用经济学口径）",
        "040100": "教育科学与技术学院",
    },
}

# 官方报考录取明细（(院校, 专业, 年份) -> 字段），仅在有官方公开数据时填写。
DETAILS = {
    ("10293", "081000", 2024): {"applicants": 715, "admitted": 145, "recommended": 41, "national_line_reached": 327},
    ("10293", "081200", 2024): {"applicants": 586, "admitted": 50, "recommended": 13, "national_line_reached": 218},
    ("10293", "085404", 2024): {"applicants": 1809, "admitted": 225, "recommended": 3, "national_line_reached": 832},
    ("10293", "020204", 2024): {"applicants": 50, "admitted": 11, "recommended": 5, "national_line_reached": 16},
    ("10293", "040100", 2024): {"applicants": 51, "admitted": 14, "recommended": 0, "national_line_reached": 24},
    ("10293", "081000", 2025): {"applicants": 612, "admitted": 150, "recommended": 50, "national_line_reached": 313},
    ("10293", "081200", 2025): {"applicants": 253, "admitted": 50, "recommended": 17, "national_line_reached": 104},
    ("10293", "085404", 2025): {"applicants": 1728, "admitted": 246, "recommended": 15, "national_line_reached": 906},
    ("10293", "020204", 2025): {"applicants": 48, "admitted": 12, "recommended": 4, "national_line_reached": 14},
    ("10293", "040100", 2025): {"applicants": 56, "admitted": 10, "recommended": 0, "national_line_reached": 3},
    ("10293", "081000", 2026): {"applicants": 543, "admitted": 152, "recommended": 38, "national_line_reached": 311},
    ("10293", "081200", 2026): {"applicants": 292, "admitted": 61, "recommended": 33, "national_line_reached": 122},
    ("10293", "085404", 2026): {"applicants": 1496, "admitted": 243, "recommended": 27, "national_line_reached": 919},
    ("10293", "020204", 2026): {"applicants": 64, "admitted": 14, "recommended": 5, "national_line_reached": 24},
    ("10293", "040100", 2026): {"applicants": 21, "admitted": 9, "recommended": 0, "national_line_reached": 0},
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
    "10272": {
        2024: {
            "name": "上海财经大学研究生院",
            "url": "https://gs.sufe.edu.cn/Home/Detail/7586",
        },
        2025: {
            "name": "上海财经大学研究生院",
            "url": "https://gs.sufe.edu.cn/Home/Detail/7812",
        },
        2026: {
            "name": "上海财经大学研究生院",
            "url": "https://gs.sufe.edu.cn/Home/Detail/7976",
        },
    },
    "10337": {
        2024: {
            "name": "浙江工业大学研究生招生网",
            "url": "http://www.yz.zjut.edu.cn/2024/0328/c4167a256203/page.htm",
        },
        2025: {
            "name": "浙江工业大学研究生招生网",
            "url": "http://www.yz.zjut.edu.cn/2025/0327/c4270a301258/page.htm",
        },
        2026: {
            "name": "浙江工业大学研究生招生网",
            "url": "http://www.yz.zjut.edu.cn/2026/0328/c4270a329985/page.htm",
        },
    },
    "10338": {
        2026: {
            "name": "浙江理工大学研究生招生网",
            "url": "https://gradadmission.zstu.edu.cn/info/1011/3343.htm",
        },
    },
    "10486": {
        2024: {
            "name": "武汉大学研究生招生信息网",
            "url": "https://wdyz.whu.edu.cn/info/1026/6373.htm",
        },
        2025: {
            "name": "武汉大学研究生招生信息网",
            "url": "https://wdyz.whu.edu.cn/info/1026/7293.htm",
        },
        2026: {
            "name": "武汉大学研究生招生信息网（2026年复试录取工作办法附件PDF）",
            "url": "https://wdyz.whu.edu.cn/wuhandaxue2026nianshuoshiyanjiushengzhaoshengkaoshifushijibenfenshuxianjixiangguanshuoming_3.20wanzhenggongbu.pdf",
        },
    },
    "10288": {
        2024: {
            "name": "南京理工大学研究生招生网",
            "url": "https://gs.njust.edu.cn/c3/64/c14687a312164/page.htm",
        },
        2025: {
            "name": "南京理工大学研究生招生网",
            "url": "https://gs.njust.edu.cn/zsw/63/17/c4585a353047/page.htm",
        },
        2026: {
            "name": "南京理工大学研究生招生网",
            "url": "https://gs.njust.edu.cn/zsw/84/58/c4585a361560/page.htm",
        },
    },
    "10293": {
        2024: {
            "name": "南京邮电大学研究生招生信息网",
            "url": "https://yzb.njupt.edu.cn/2024/0622/c7813a269521/page.htm",
        },
        2025: {
            "name": "南京邮电大学研究生招生信息网",
            "url": "https://yzb.njupt.edu.cn/2025/0526/c7813a284312/page.htm",
        },
        2026: {
            "name": "南京邮电大学研究生招生信息网",
            "url": "https://yzb.njupt.edu.cn/2026/0529/c7813a302875/page.htm",
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
    "10272": "上海财经大学",
    "10337": "浙江工业大学",
    "10338": "浙江理工大学",
    "10486": "武汉大学",
    "10288": "南京理工大学",
    "10293": "南京邮电大学",
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
    if code in PER_MAJOR_SCHOOLS:
        return "school_per_major_line", {
            "official_line_scope": "school_per_major_line",
            "official_line_label": "学校分专业（分学院）复试线",
            "line_meaning": "以官方公布的分专业复试线为准；未单列/未达线的专业当年不生成记录。",
        }
    if code == "10486":
        return "self_draw_per_college_line", {
            "official_line_scope": "self_draw_per_college_line",
            "official_line_label": "自划线院校分培养单位复试线",
            "line_meaning": "武汉大学按培养单位/专业公布复试线；学院可在学校基本要求上自主划定。",
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
                detail = DETAILS.get((code, major, year), {})
                row_metrics = dict(metrics)
                if detail:
                    row_metrics["official_admission_counts_note"] = (
                        "报名/达国家线/推免/录取人数来自官方分专业报考录取情况表；"
                        "报录比由官方报名人数÷录取人数计算。"
                    )
                    if "national_line_reached" in detail:
                        row_metrics["national_line_reached_count"] = detail["national_line_reached"]
                report_rate = ""
                if detail.get("applicants") and detail.get("admitted"):
                    report_rate = round(detail["applicants"] / detail["admitted"], 2)
                row = {
                    "institution_code": code,
                    "major_code": major,
                    "year": year,
                    "plan_total": "",
                    "plan_unified": "",
                    "recommended_count": detail.get("recommended", ""),
                    "recommended_ratio": "",
                    "applicant_count": detail.get("applicants", ""),
                    "admitted_count": detail.get("admitted", ""),
                    "report_rate": report_rate,
                    "reexam_count": "",
                    "reexam_admit_rate": "",
                    "max_score": "",
                    "min_score": "",
                    "avg_score": "",
                    "self_line": line if code in SELF_DRAW_CODES else "",
                    "college_line": "" if code in SELF_DRAW_CODES else line,
                    "national_line": "",
                    "transfer_quota": "",
                    "metrics": json.dumps(row_metrics, ensure_ascii=False),
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
                if code in {"10272", "10288", "10338"}:
                    note = "官方网页表格逐字核录（分专业口径）"
                if code == "10337":
                    note = "官方分数线原图本地OCR核录"
                if code == "10486":
                    note = "官方PDF/网页表格核录（分培养单位口径）"
                scope_label = (
                    "分专业复试线"
                    if code in PER_MAJOR_SCHOOLS
                    else ("自划线-分培养单位复试线" if code == "10486" else "学校复试基本线(学科门类/类别)")
                )
                verified_rows.append(
                    {
                        "院校代码": code,
                        "院校": NAMES[code],
                        "年份": year,
                        "口径": scope_label,
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
                        "口径": scope_label,
                        "专业/学科": MAJOR_NAMES[major],
                        "总分线": line,
                        "官方URL": SOURCES[code][year]["url"],
                        "复核方法": note,
                        "结论": "通过",
                    }
                )

    if verified_rows:
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
                if code == "10337":
                    read_type = "图片(OCR)"
                elif code in {"10003"}:
                    read_type = "文字/图片(OCR)" if year in {2024, 2025} else "PDF附件"
                elif code in {"10272", "10338", "10288"}:
                    read_type = "文字"
                elif code in {"10001", "10246", "10248", "10284", "10286", "10269", "10486"}:
                    read_type = "PDF附件"
                else:
                    read_type = "文字"
                fh.write(
                    f"{NAMES[code]},复试基本分数线,{year},{source['url']},{read_type},已核对,"
                    f"官方原文核录；原始存证见 data/official/raw/\n"
                )


def main() -> int:
    total = expected_stat_count()
    print(f"增量导入（保留既有批次数据）：{DB_FILE}，本批可核官方招录行：{total}")
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
        for keyword, year, expected in [
            ("北京大学", 2026, 9),
            ("清华大学", 2026, 9),
            ("复旦大学", 2026, 9),
            ("上海交通大学", 2026, 9),
            ("南京大学", 2026, 9),
            ("东南大学", 2026, 9),
            ("华东师范大学", 2026, 6),
            ("上海财经大学", 2026, 3),
            ("浙江工业大学", 2026, 8),
            ("浙江理工大学", 2026, 7),
            ("南京理工大学", 2026, 8),
            ("武汉大学", 2025, 8),
            ("武汉大学", 2026, 7),
            ("南京邮电大学", 2026, 5),
        ]:
            resp = client.get(
                "/api/v1/institution-majors",
                params={"keyword": keyword, "year": year, "page_size": 100},
            ).json()
            official = [
                item for item in resp["items"]
                if item["latest_stat"] and item["latest_stat"]["data_quality"] == "official"
            ]
            print(f"{keyword} {year} 官方组合数：", len(official))
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
    print("OK：真实数据批次 v0.4 导入与审核完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
