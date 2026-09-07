"""学习计划生成与进度统计。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..models import PlanTask, StudyPlan


SUBJECT_ORDER = ["政治", "英语", "数学", "专业课"]


def _stage_for_progress(progress: float) -> str:
    if progress < 0.3:
        return "基础期"
    if progress < 0.7:
        return "强化期"
    return "冲刺期"


def _subject_title(stage: str, subject: str) -> str:
    if stage == "基础期":
        return f"{subject}基础：知识点梳理"
    if stage == "强化期":
        return f"{subject}强化：重点专题与真题"
    return f"{subject}冲刺：模拟卷与查漏补缺"


def _gap_weights(target_scores: dict[str, Any], current_scores: dict[str, Any]) -> dict[str, float]:
    subjects = [s for s in SUBJECT_ORDER if s in target_scores] or list(target_scores.keys())
    weights: dict[str, float] = {}
    for subject in subjects:
        target = float(target_scores.get(subject, 0) or 0)
        current = float(current_scores.get(subject, target) if subject in current_scores else target)
        gap = max(target - current, 10.0)
        weights[subject] = gap
    total = sum(weights.values()) or len(subjects)
    return {subject: weight / total for subject, weight in weights.items()}


def generate_plan_tasks(plan: StudyPlan) -> list[PlanTask]:
    """为计划生成每日任务，按科目短板分配时长。"""
    weights = _gap_weights(plan.target_scores, plan.current_scores)
    subjects = list(weights.keys())
    tasks: list[PlanTask] = []

    total_days = max((plan.end_date - plan.start_date).days + 1, 1)
    cursor = plan.start_date
    order = 0

    while cursor <= plan.end_date:
        progress = (cursor - plan.start_date).days / max(total_days - 1, 1)
        stage = _stage_for_progress(progress)
        remaining = plan.daily_minutes
        allocated: list[tuple[str, int]] = []

        for subject in subjects[:-1]:
            minutes = int(plan.daily_minutes * weights[subject])
            allocated.append((subject, minutes))
            remaining -= minutes

        allocated.append((subjects[-1], max(remaining, 0)))

        for index, (subject, minutes) in enumerate(allocated):
            if minutes <= 0:
                continue
            order += 1
            tasks.append(
                PlanTask(
                    plan_id=plan.id,
                    subject=subject,
                    title=_subject_title(stage, subject),
                    task_date=cursor,
                    planned_minutes=minutes,
                    status="pending",
                    sort_order=order,
                    source="generated",
                )
            )
        cursor += timedelta(days=1)

    return tasks


def build_study_progress(check_ins: list[Any], start: date | None, end: date | None) -> dict[str, Any]:
    """由打卡记录计算进度指标。"""
    if not check_ins:
        return {
            "total_days": 0,
            "total_minutes": 0,
            "consecutive_days": 0,
            "completion_rate": 0.0,
            "subject_progress": {},
            "daily_curve": [],
        }

    dates = sorted({c.date for c in check_ins})
    total_minutes = sum(c.duration_minutes for c in check_ins)
    total_days = len(dates)
    avg_completion = sum(float(c.completion) for c in check_ins) / len(check_ins)

    consecutive = 1
    best = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            consecutive += 1
            best = max(best, consecutive)
        else:
            consecutive = 1
    best = best if dates else 0

    subject_minutes: dict[str, int] = {}
    for c in check_ins:
        subject_minutes[c.subject] = subject_minutes.get(c.subject, 0) + c.duration_minutes

    daily: dict[date, int] = {}
    for c in check_ins:
        daily[c.date] = daily.get(c.date, 0) + c.duration_minutes

    curve_start = start or (min(dates) if dates else date.today())
    curve_end = end or (max(dates) if dates else date.today())
    cursor = curve_start
    daily_curve: list[dict[str, Any]] = []
    while cursor <= curve_end:
        daily_curve.append(
            {"date": cursor.isoformat(), "minutes": daily.get(cursor, 0)}
        )
        cursor += timedelta(days=1)

    return {
        "total_days": total_days,
        "total_minutes": total_minutes,
        "consecutive_days": best,
        "completion_rate": round(avg_completion, 2),
        "subject_progress": subject_minutes,
        "daily_curve": daily_curve,
    }


def rollover_incomplete(plan: StudyPlan, tasks: list[PlanTask], target_date: date) -> int:
    """把截止到目标日仍未完成的过期任务顺延到目标日。"""
    moved = 0
    for task in tasks:
        if task.status != "pending" or task.task_date >= target_date:
            continue
        task.original_date = task.original_date or task.task_date
        task.task_date = target_date
        task.is_rolled_over = True
        moved += 1
    return moved
