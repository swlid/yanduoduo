"""学习计划、任务与顺延接口。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import PlanTask, StudyPlan
from ..schemas import (
    PlanGenerateRequest,
    PlanTaskOut,
    StudyPlanDetailOut,
    StudyPlanOut,
)
from ..services.planner import generate_plan_tasks, rollover_incomplete


router = APIRouter(prefix="/plans", tags=["学习计划"])


def _task_out(task: PlanTask) -> dict:
    return PlanTaskOut.model_validate(task).model_dump(mode="json")


def _plan_detail(plan: StudyPlan) -> dict:
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "title": plan.title,
        "institution_major_id": plan.institution_major_id,
        "target_total_score": plan.target_total_score,
        "target_scores": plan.target_scores,
        "current_scores": plan.current_scores,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat(),
        "daily_minutes": plan.daily_minutes,
        "reminder_time": plan.reminder_time,
        "status": plan.status,
        "plan_tasks": [_task_out(task) for task in plan.plan_tasks],
    }


def _load_plan(db: Session, plan_id: str) -> StudyPlan | None:
    stmt = (
        select(StudyPlan)
        .where(StudyPlan.id == plan_id)
        .options(selectinload(StudyPlan.plan_tasks))
    )
    return db.scalar(stmt)


@router.post("/generate", response_model=StudyPlanDetailOut, status_code=201)
def create_plan(
    payload: PlanGenerateRequest,
    db: Session = Depends(get_db),
) -> StudyPlanDetailOut:
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
    if not payload.target_scores:
        raise HTTPException(status_code=400, detail="目标科目分数不能为空")
    if payload.daily_minutes <= 0:
        raise HTTPException(status_code=400, detail="每日学习时长必须大于 0")

    plan = StudyPlan(
        user_id=payload.user_id,
        title=payload.title or "考研学习计划",
        institution_major_id=payload.institution_major_id,
        target_total_score=payload.target_total_score,
        target_scores=payload.target_scores,
        current_scores=payload.current_scores,
        start_date=payload.start_date,
        end_date=payload.end_date,
        daily_minutes=payload.daily_minutes,
        reminder_time=payload.reminder_time,
        status="active",
    )
    db.add(plan)
    db.flush()

    tasks = generate_plan_tasks(plan)
    db.add_all(tasks)
    db.commit()

    refreshed = _load_plan(db, plan.id)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="计划生成失败")
    return StudyPlanDetailOut.model_validate(_plan_detail(refreshed))


@router.get("", response_model=list[StudyPlanOut])
def list_plans(
    user_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[StudyPlanOut]:
    stmt = select(StudyPlan)
    if user_id:
        stmt = stmt.where(StudyPlan.user_id == user_id)
    rows = db.scalars(stmt.order_by(StudyPlan.created_at.desc())).all()
    return [StudyPlanOut.model_validate(row) for row in rows]


@router.get("/{plan_id}", response_model=StudyPlanDetailOut)
def get_plan(plan_id: str, db: Session = Depends(get_db)) -> StudyPlanDetailOut:
    plan = _load_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    return StudyPlanDetailOut.model_validate(_plan_detail(plan))


@router.get("/{plan_id}/calendar", response_model=dict)
def plan_calendar(
    plan_id: str,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
) -> dict:
    plan = _load_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="学习计划不存在")

    start = start or plan.start_date
    end = end or plan.end_date
    tasks = [
        task
        for task in plan.plan_tasks
        if start <= task.task_date <= end
    ]
    return {
        "plan_id": plan.id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "items": [_task_out(task) for task in tasks],
    }


@router.post("/{plan_id}/rollover", response_model=StudyPlanDetailOut)
def rollover_plan(
    plan_id: str,
    target_date: date | None = None,
    db: Session = Depends(get_db),
) -> StudyPlanDetailOut:
    plan = _load_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="学习计划不存在")

    target = target_date or date.today()
    moved = rollover_incomplete(plan, plan.plan_tasks, target)
    db.commit()
    return StudyPlanDetailOut.model_validate(
        {
            **_plan_detail(plan),
            "rollover_count": moved,
        }
    )


@router.post(
    "/{plan_id}/tasks/{task_id}/complete",
    response_model=PlanTaskOut,
)
def complete_task(
    plan_id: str,
    task_id: str,
    db: Session = Depends(get_db),
) -> PlanTaskOut:
    plan = _load_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="学习计划不存在")

    task = next((t for t in plan.plan_tasks if t.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    task.status = "done"
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    return PlanTaskOut.model_validate(task)
