"""Mock 种子数据。

所有数据均标记 `data_quality=mock`，仅用于打通产品流程；
真实数据后续通过后台导入/审核通道接入。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import (
    AdmissionStat,
    Institution,
    InstitutionMajor,
    Major,
    ProcessNode,
    TaskTemplate,
)


INSTITUTIONS: list[dict[str, Any]] = [
    {"id": "inst-001", "code": "10001", "name": "北京大学", "short_name": "北大", "province": "北京", "city": "北京", "level": "985", "category": "综合", "is_self_draw": True},
    {"id": "inst-002", "code": "10003", "name": "清华大学", "short_name": "清华", "province": "北京", "city": "北京", "level": "985", "category": "理工", "is_self_draw": True},
    {"id": "inst-003", "code": "10246", "name": "复旦大学", "short_name": "复旦", "province": "上海", "city": "上海", "level": "985", "category": "综合", "is_self_draw": True},
    {"id": "inst-004", "code": "10248", "name": "上海交通大学", "short_name": "上交", "province": "上海", "city": "上海", "level": "985", "category": "综合", "is_self_draw": True},
    {"id": "inst-005", "code": "10335", "name": "浙江大学", "short_name": "浙大", "province": "浙江", "city": "杭州", "level": "985", "category": "综合", "is_self_draw": True},
    {"id": "inst-006", "code": "10284", "name": "南京大学", "short_name": "南大", "province": "江苏", "city": "南京", "level": "985", "category": "综合", "is_self_draw": True},
    {"id": "inst-007", "code": "10286", "name": "东南大学", "short_name": "东大", "province": "江苏", "city": "南京", "level": "985", "category": "理工", "is_self_draw": True},
    {"id": "inst-008", "code": "10269", "name": "华东师范大学", "short_name": "华师大", "province": "上海", "city": "上海", "level": "985", "category": "师范", "is_self_draw": False},
    {"id": "inst-009", "code": "10486", "name": "武汉大学", "short_name": "武大", "province": "湖北", "city": "武汉", "level": "985", "category": "综合", "is_self_draw": True},
    {"id": "inst-010", "code": "10701", "name": "西安电子科技大学", "short_name": "西电", "province": "陕西", "city": "西安", "level": "211", "category": "理工", "is_self_draw": False},
    {"id": "inst-011", "code": "10293", "name": "南京邮电大学", "short_name": "南邮", "province": "江苏", "city": "南京", "level": "双一流", "category": "理工", "is_self_draw": False},
    {"id": "inst-012", "code": "10337", "name": "浙江工业大学", "short_name": "浙工大", "province": "浙江", "city": "杭州", "level": "普通", "category": "理工", "is_self_draw": False},
    {"id": "inst-013", "code": "10336", "name": "杭州电子科技大学", "short_name": "杭电", "province": "浙江", "city": "杭州", "level": "普通", "category": "理工", "is_self_draw": False},
    {"id": "inst-014", "code": "10272", "name": "上海财经大学", "short_name": "上财", "province": "上海", "city": "上海", "level": "211", "category": "财经", "is_self_draw": False},
    {"id": "inst-015", "code": "10276", "name": "华东政法大学", "short_name": "华政", "province": "上海", "city": "上海", "level": "普通", "category": "政法", "is_self_draw": False},
    {"id": "inst-016", "code": "14430", "name": "中国科学院大学", "short_name": "国科大", "province": "北京", "city": "北京", "level": "双一流", "category": "科研院所", "is_self_draw": False},
    {"id": "inst-017", "code": "10280", "name": "上海大学", "short_name": "上大", "province": "上海", "city": "上海", "level": "211", "category": "综合", "is_self_draw": False},
    {"id": "inst-018", "code": "10285", "name": "苏州大学", "short_name": "苏大", "province": "江苏", "city": "苏州", "level": "211", "category": "综合", "is_self_draw": False},
    {"id": "inst-019", "code": "10288", "name": "南京理工大学", "short_name": "南理工", "province": "江苏", "city": "南京", "level": "211", "category": "理工", "is_self_draw": False},
    {"id": "inst-020", "code": "10338", "name": "浙江理工大学", "short_name": "浙理工", "province": "浙江", "city": "杭州", "level": "普通", "category": "理工", "is_self_draw": False},
]


MAJORS: list[dict[str, Any]] = [
    {"id": "major-001", "code": "081200", "name": "计算机科学与技术", "discipline_gate": "工学", "discipline_level1": "计算机科学与技术", "degree_type": "学硕", "is_cross_allowed": True},
    {"id": "major-002", "code": "085404", "name": "计算机技术", "discipline_gate": "工学", "discipline_level1": "电子信息", "degree_type": "专硕", "is_cross_allowed": True},
    {"id": "major-003", "code": "085405", "name": "软件工程", "discipline_gate": "工学", "discipline_level1": "电子信息", "degree_type": "专硕", "is_cross_allowed": True},
    {"id": "major-004", "code": "081000", "name": "信息与通信工程", "discipline_gate": "工学", "discipline_level1": "信息与通信工程", "degree_type": "学硕", "is_cross_allowed": True},
    {"id": "major-005", "code": "085400", "name": "电子信息", "discipline_gate": "工学", "discipline_level1": "电子信息", "degree_type": "专硕", "is_cross_allowed": True},
    {"id": "major-006", "code": "080200", "name": "机械工程", "discipline_gate": "工学", "discipline_level1": "机械工程", "degree_type": "学硕", "is_cross_allowed": True},
    {"id": "major-007", "code": "020204", "name": "金融学", "discipline_gate": "经济学", "discipline_level1": "应用经济学", "degree_type": "学硕", "is_cross_allowed": False, "cross_condition": "通常要求经济学或数学相关背景"},
    {"id": "major-008", "code": "025100", "name": "金融", "discipline_gate": "经济学", "discipline_level1": "金融", "degree_type": "专硕", "is_cross_allowed": True},
    {"id": "major-009", "code": "040100", "name": "教育学", "discipline_gate": "教育学", "discipline_level1": "教育学", "degree_type": "学硕", "is_cross_allowed": True},
    {"id": "major-010", "code": "030100", "name": "法学", "discipline_gate": "法学", "discipline_level1": "法学", "degree_type": "学硕", "is_cross_allowed": False, "cross_condition": "部分院校要求法学本科背景"},
    {"id": "major-011", "code": "035101", "name": "法律（非法学）", "discipline_gate": "法学", "discipline_level1": "法律", "degree_type": "专硕", "is_cross_allowed": True},
    {"id": "major-012", "code": "035102", "name": "法律（法学）", "discipline_gate": "法学", "discipline_level1": "法律", "degree_type": "专硕", "is_cross_allowed": False, "cross_condition": "要求法学本科背景（法学第二学士学位等以当年招生简章为准）"},
]


# 组合：院校、专业、院系、学制、学费、初试、复试、招生基础数、报考基础数、平均分基础值、国家线
COMBOS: list[dict[str, Any]] = [
    {"id": "im-001", "institution_id": "inst-002", "major_id": "major-001", "faculty_name": "计算机科学与技术系", "length": 3, "tuition": "8000元/年", "plan": 25, "applicants": 780, "avg": 392, "national": 273, "difficulty": "冲刺"},
    {"id": "im-002", "institution_id": "inst-002", "major_id": "major-002", "faculty_name": "计算机科学与技术系", "length": 3, "tuition": "20000元/年", "plan": 60, "applicants": 1500, "avg": 368, "national": 273, "difficulty": "冲刺"},
    {"id": "im-003", "institution_id": "inst-003", "major_id": "major-002", "faculty_name": "计算机科学技术学院", "length": 3, "tuition": "18000元/年", "plan": 55, "applicants": 1200, "avg": 360, "national": 273, "difficulty": "冲刺"},
    {"id": "im-004", "institution_id": "inst-004", "major_id": "major-002", "faculty_name": "电子信息与电气工程学院", "length": 2.5, "tuition": "24000元/年", "plan": 70, "applicants": 1400, "avg": 362, "national": 273, "difficulty": "冲刺"},
    {"id": "im-005", "institution_id": "inst-005", "major_id": "major-001", "faculty_name": "计算机科学与技术学院", "length": 3, "tuition": "8000元/年", "plan": 30, "applicants": 900, "avg": 385, "national": 273, "difficulty": "冲刺"},
    {"id": "im-006", "institution_id": "inst-005", "major_id": "major-003", "faculty_name": "软件学院", "length": 3, "tuition": "20000元/年", "plan": 45, "applicants": 950, "avg": 355, "national": 273, "difficulty": "稳妥"},
    {"id": "im-007", "institution_id": "inst-006", "major_id": "major-001", "faculty_name": "计算机科学与技术系", "length": 3, "tuition": "8000元/年", "plan": 35, "applicants": 820, "avg": 372, "national": 273, "difficulty": "冲刺"},
    {"id": "im-008", "institution_id": "inst-007", "major_id": "major-002", "faculty_name": "计算机科学与工程学院", "length": 3, "tuition": "18000元/年", "plan": 80, "applicants": 1050, "avg": 352, "national": 273, "difficulty": "稳妥"},
    {"id": "im-009", "institution_id": "inst-010", "major_id": "major-002", "faculty_name": "计算机科学与技术学院", "length": 3, "tuition": "12000元/年", "plan": 90, "applicants": 1150, "avg": 345, "national": 273, "difficulty": "稳妥"},
    {"id": "im-010", "institution_id": "inst-011", "major_id": "major-002", "faculty_name": "计算机学院", "length": 3, "tuition": "12000元/年", "plan": 110, "applicants": 980, "avg": 328, "national": 273, "difficulty": "保底"},
    {"id": "im-011", "institution_id": "inst-013", "major_id": "major-002", "faculty_name": "计算机学院", "length": 3, "tuition": "10000元/年", "plan": 130, "applicants": 860, "avg": 315, "national": 273, "difficulty": "保底"},
    {"id": "im-012", "institution_id": "inst-004", "major_id": "major-005", "faculty_name": "电子信息与电气工程学院", "length": 2.5, "tuition": "24000元/年", "plan": 65, "applicants": 1250, "avg": 355, "national": 273, "difficulty": "冲刺"},
    {"id": "im-013", "institution_id": "inst-010", "major_id": "major-004", "faculty_name": "通信工程学院", "length": 3, "tuition": "8000元/年", "plan": 40, "applicants": 760, "avg": 338, "national": 273, "difficulty": "稳妥"},
    {"id": "im-014", "institution_id": "inst-011", "major_id": "major-005", "faculty_name": "通信与信息工程学院", "length": 3, "tuition": "12000元/年", "plan": 120, "applicants": 720, "avg": 322, "national": 273, "difficulty": "保底"},
    {"id": "im-015", "institution_id": "inst-012", "major_id": "major-006", "faculty_name": "机械工程学院", "length": 3, "tuition": "8000元/年", "plan": 45, "applicants": 420, "avg": 310, "national": 273, "difficulty": "稳妥"},
    {"id": "im-016", "institution_id": "inst-014", "major_id": "major-007", "faculty_name": "金融学院", "length": 3, "tuition": "8000元/年", "plan": 20, "applicants": 560, "avg": 392, "national": 346, "difficulty": "冲刺"},
    {"id": "im-017", "institution_id": "inst-014", "major_id": "major-008", "faculty_name": "金融学院", "length": 2, "tuition": "98000元/全程", "plan": 75, "applicants": 1500, "avg": 378, "national": 346, "difficulty": "冲刺"},
    {"id": "im-018", "institution_id": "inst-008", "major_id": "major-009", "faculty_name": "教育学部", "length": 3, "tuition": "8000元/年", "plan": 35, "applicants": 680, "avg": 360, "national": 351, "difficulty": "冲刺"},
    {"id": "im-019", "institution_id": "inst-015", "major_id": "major-010", "faculty_name": "法律学院", "length": 3, "tuition": "8000元/年", "plan": 28, "applicants": 720, "avg": 358, "national": 335, "difficulty": "稳妥"},
    {"id": "im-020", "institution_id": "inst-016", "major_id": "major-001", "faculty_name": "计算机科学与技术学院", "length": 3, "tuition": "8000元/年", "plan": 15, "applicants": 480, "avg": 376, "national": 273, "difficulty": "冲刺"},
    {"id": "im-021", "institution_id": "inst-017", "major_id": "major-002", "faculty_name": "计算机工程与科学学院", "length": 3, "tuition": "16000元/年", "plan": 85, "applicants": 900, "avg": 346, "national": 273, "difficulty": "稳妥"},
    {"id": "im-022", "institution_id": "inst-018", "major_id": "major-002", "faculty_name": "计算机科学与技术学院", "length": 3, "tuition": "14000元/年", "plan": 70, "applicants": 850, "avg": 344, "national": 273, "difficulty": "稳妥"},
    {"id": "im-023", "institution_id": "inst-019", "major_id": "major-002", "faculty_name": "计算机科学与工程学院", "length": 3, "tuition": "12000元/年", "plan": 65, "applicants": 880, "avg": 347, "national": 273, "difficulty": "稳妥"},
    {"id": "im-024", "institution_id": "inst-020", "major_id": "major-002", "faculty_name": "计算机科学与技术学院", "length": 3, "tuition": "10000元/年", "plan": 90, "applicants": 700, "avg": 335, "national": 273, "difficulty": "保底"},
]

MAJOR_BY_ID = {item["id"]: item for item in MAJORS}

TASK_TEMPLATES: list[dict[str, Any]] = [
    {"id": "tpl-001", "stage": "基础期", "subject": "政治", "title": "马原与史纲基础梳理", "sort_order": 1, "default_minutes": 60},
    {"id": "tpl-002", "stage": "基础期", "subject": "英语", "title": "考研词汇与长难句", "sort_order": 2, "default_minutes": 90},
    {"id": "tpl-003", "stage": "基础期", "subject": "数学", "title": "高数基础与教材习题", "sort_order": 3, "default_minutes": 120},
    {"id": "tpl-004", "stage": "基础期", "subject": "专业课", "title": "专业课教材第一轮精读", "sort_order": 4, "default_minutes": 90},
    {"id": "tpl-005", "stage": "强化期", "subject": "政治", "title": "选择题题库强化", "sort_order": 1, "default_minutes": 60},
    {"id": "tpl-006", "stage": "强化期", "subject": "英语", "title": "阅读真题精读", "sort_order": 2, "default_minutes": 90},
    {"id": "tpl-007", "stage": "强化期", "subject": "数学", "title": "强化讲义与专题训练", "sort_order": 3, "default_minutes": 120},
    {"id": "tpl-008", "stage": "强化期", "subject": "专业课", "title": "重点章节与历年真题", "sort_order": 4, "default_minutes": 90},
    {"id": "tpl-009", "stage": "冲刺期", "subject": "政治", "title": "时政与主观题背诵", "sort_order": 1, "default_minutes": 60},
    {"id": "tpl-010", "stage": "冲刺期", "subject": "英语", "title": "作文模板与全真模考", "sort_order": 2, "default_minutes": 90},
    {"id": "tpl-011", "stage": "冲刺期", "subject": "数学", "title": "真题套卷与错题复盘", "sort_order": 3, "default_minutes": 120},
    {"id": "tpl-012", "stage": "冲刺期", "subject": "专业课", "title": "高频考点与模拟卷", "sort_order": 4, "default_minutes": 90},
]

PROCESS_NODES: list[dict[str, Any]] = [
    {"id": "node-001", "key": "syllabus", "name": "考试大纲发布", "stage": "强化期", "year": 2026, "actual_date": "2026-09-10", "advance_days": 3, "guide": "关注研招网和报考院校研究生院官网，比对大纲变化。"},
    {"id": "node-002", "key": "pre_register", "name": "预报名", "stage": "冲刺期", "year": 2026, "actual_date": "2026-09-24", "advance_days": 5, "guide": "登录研招网填写考生信息，预报名信息可在正式报名阶段修改。"},
    {"id": "node-003", "key": "register", "name": "正式报名", "stage": "冲刺期", "year": 2026, "actual_date": "2026-10-10", "advance_days": 7, "guide": "准备身份证、学历信息、报考点要求材料，在研招网完成报名并缴费。"},
    {"id": "node-004", "key": "confirm", "name": "网上/现场确认", "stage": "冲刺期", "year": 2026, "actual_date": "2026-11-05", "advance_days": 7, "guide": "按报考点要求上传照片和材料，确认报名信息无误。"},
    {"id": "node-005", "key": "admission_ticket", "name": "打印准考证", "stage": "冲刺期", "year": 2026, "actual_date": "2026-12-14", "advance_days": 3, "guide": "登录研招网下载并打印准考证，核对考场和时间。"},
    {"id": "node-006", "key": "exam", "name": "全国硕士研究生初试", "stage": "冲刺期", "year": 2026, "actual_date": "2026-12-26", "advance_days": 14, "guide": "提前熟悉考场路线，准备准考证、身份证和考试文具。"},
    {"id": "node-007", "key": "score", "name": "初试成绩公布", "stage": "复试期", "year": 2027, "actual_date": "2027-02-20", "advance_days": 7, "guide": "登录省级考试院或研招网查询成绩，关注成绩复核安排。"},
    {"id": "node-008", "key": "self_line", "name": "自划线院校分数线公布", "stage": "复试期", "year": 2027, "actual_date": "2027-03-05", "advance_days": 7, "guide": "关注 34 所自划线院校官网发布的复试基本分数线。"},
    {"id": "node-009", "key": "national_line", "name": "国家线公布", "stage": "复试期", "year": 2027, "actual_date": "2027-03-10", "advance_days": 7, "guide": "对照国家线判断是否进入复试或具备调剂资格。"},
    {"id": "node-010", "key": "reexam", "name": "复试", "stage": "复试期", "year": 2027, "actual_date": "2027-03-20", "advance_days": 14, "guide": "准备资格审查材料、复试笔试和面试，关注院校复试通知。"},
    {"id": "node-011", "key": "transfer_open", "name": "调剂系统开放", "stage": "复试期", "year": 2027, "actual_date": "2027-03-31", "advance_days": 7, "guide": "在研招网调剂系统填报调剂志愿，及时确认复试通知。"},
    {"id": "node-012", "key": "transfer_close", "name": "调剂系统关闭", "stage": "复试期", "year": 2027, "actual_date": "2027-04-30", "advance_days": 7, "guide": "确认最终待录取状态，完成调剂流程。"},
    {"id": "node-013", "key": "admission_archive", "name": "录取与调档", "stage": "录取期", "year": 2027, "actual_date": "2027-05-20", "advance_days": 7, "guide": "按录取院校要求办理调档、体检和入学前手续。"},
]


def _decimal(value: float | int) -> Decimal:
    return Decimal(str(value))


def _make_stat(
    institution_major_id: str,
    year: int,
    combo: dict[str, Any],
) -> AdmissionStat:
    drift = year - 2024
    plan = max(8, combo["plan"] + drift * 3)
    applicants = max(80, combo["applicants"] + drift * 45)
    avg = combo["avg"] + drift * 2
    national = combo["national"]
    admitted = max(5, round(plan * 0.58))
    unified = max(4, round(plan * 0.72))
    recommended = max(0, plan - unified)
    reexam_count = max(admitted, round(admitted * 1.2))

    return AdmissionStat(
        id=f"stat-{institution_major_id}-{year}",
        institution_major_id=institution_major_id,
        year=year,
        plan_total=plan,
        plan_unified=unified,
        recommended_count=recommended,
        recommended_ratio=_decimal(round(recommended / plan, 4)) if plan else 0,
        applicant_count=applicants,
        admitted_count=admitted,
        report_rate=_decimal(round(applicants / admitted, 2)),
        reexam_count=reexam_count,
        reexam_admit_rate=_decimal(round(reexam_count / admitted, 2)),
        max_score=_decimal(round(avg + 17, 2)),
        min_score=_decimal(round(avg - 10, 2)),
        avg_score=_decimal(avg),
        national_line=_decimal(national),
        self_line=_decimal(round(avg - 2, 2)) if year == 2025 else None,
        college_line=_decimal(round(avg - 4, 2)),
        transfer_quota=max(0, 2 - drift),
        metrics={
            "difficulty": combo["difficulty"],
            "trend": "上升" if drift > 0 else "平稳",
            "is_mock": True,
        },
        source_url="https://example.com/mock",
        source_name="研多多 Mock 示例数据",
        source_year=year,
        data_quality="mock",
        review_status="approved",
    )


def seed(db: Session | None = None) -> int:
    """写入 Mock 数据并返回写入的招录记录数。"""
    own_session = db is None
    session = db or SessionLocal()
    try:
        session.execute(AdmissionStat.__table__.delete())
        session.execute(InstitutionMajor.__table__.delete())
        session.execute(Major.__table__.delete())
        session.execute(Institution.__table__.delete())
        session.execute(TaskTemplate.__table__.delete())
        session.execute(ProcessNode.__table__.delete())

        for item in INSTITUTIONS:
            session.add(Institution(**item))
        for item in MAJORS:
            session.add(Major(**item))
        for item in TASK_TEMPLATES:
            session.add(TaskTemplate(**item))
        for item in PROCESS_NODES:
            node_data = dict(item)
            node_data["actual_date"] = date.fromisoformat(item["actual_date"])
            session.add(ProcessNode(**node_data))
        session.flush()

        for combo in COMBOS:
            degree_type = MAJOR_BY_ID[combo["major_id"]]["degree_type"]
            im = InstitutionMajor(
                id=combo["id"],
                institution_id=combo["institution_id"],
                major_id=combo["major_id"],
                faculty_name=combo["faculty_name"],
                study_mode="全日制",
                length=combo.get("length"),
                tuition=combo.get("tuition"),
                scholarship="国家助学金 6000元/年；学业奖学金按成绩评定",
                exam_basic={
                    "政治": "思想政治理论",
                    "外语": "英语一" if degree_type == "学硕" else "英语二",
                    "数学": "数学一" if combo["major_id"] in {"major-001", "major-002", "major-003", "major-004", "major-005", "major-006"} else None,
                },
                exam_major={
                    "code": "408",
                    "name": "计算机学科专业基础综合",
                    "参考书目": ["《数据结构》", "《计算机组成原理》", "《操作系统》", "《计算机网络》"],
                },
                reexam_form={"笔试": "专业综合", "面试": "综合面试", "机试": "上机编程" if combo["major_id"] in {"major-001", "major-002", "major-003"} else None},
                additional_exam=None,
                status="published",
            )
            session.add(im)
            session.flush()

            for year in (2023, 2024, 2025):
                session.add(_make_stat(im.id, year, combo))

        session.commit()
        return len(COMBOS) * 3
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def seed_if_empty() -> int:
    """数据库为空时自动写入种子数据。"""
    with SessionLocal() as session:
        count = session.scalar(select(Institution.id).limit(1))
        if count is not None:
            return 0
    return seed()


if __name__ == "__main__":
    from .db import init_db

    init_db()
    total = seed_if_empty()
    print(f"Mock 数据写入完成，共 {total} 条招录记录。")
