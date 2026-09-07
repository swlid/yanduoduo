"""学习打卡、进度可视化与周/月报告接口。"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CheckIn, StudyReport
from ..schemas import CheckInCreate, CheckInOut
from ..services.planner import build_study_progress


checkin_router = APIRouter(prefix="/check-ins", tags=["学习打卡"])
progress_router = APIRouter(prefix="/progress", tags=["进度"])
report_router = APIRouter(prefix="/reports", tags=["学习报告"])


@checkin_router.post("", response_model=CheckInOut, status_code=201)
def create_checkin(
    payload: CheckInCreate,
    db: Session = Depends(get_db),
) -> CheckInOut:
    item = CheckIn(
        user_id=payload.user_id,
        date=payload.date,
        subject=payload.subject,
        duration_minutes=payload.duration_minutes,
        completion=payload.completion,
        note=payload.note,
        is_makeup=payload.is_makeup,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return CheckInOut.model_validate(item)


@checkin_router.get("", response_model=list[CheckInOut])
def list_checkins(
    user_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    subject: str | None = None,
    db: Session = Depends(get_db),
) -> list[CheckInOut]:
    stmt = select(CheckIn)
    if user_id:
        stmt = stmt.where(CheckIn.user_id == user_id)
    if start:
        stmt = stmt.where(CheckIn.date >= start)
    if end:
        stmt = stmt.where(CheckIn.date <= end)
    if subject:
        stmt = stmt.where(CheckIn.subject == subject)
    rows = db.scalars(stmt.order_by(CheckIn.date.desc())).all()
    return [CheckInOut.model_validate(row) for row in rows]


@progress_router.get("", response_model=dict)
def get_progress(
    user_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(CheckIn)
    if user_id:
        stmt = stmt.where(CheckIn.user_id == user_id)
    if start:
        stmt = stmt.where(CheckIn.date >= start)
    if end:
        stmt = stmt.where(CheckIn.date <= end)
    rows = db.scalars(stmt.order_by(CheckIn.date)).all()
    stats = build_study_progress(list(rows), start, end)
    stats["check_in_count"] = len(rows)
    return stats


@report_router.get("/{period}", response_model=dict)
def get_report(
    period: str,
    user_id: str | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
) -> dict:
    if period not in {"week", "month"}:
        raise HTTPException(status_code=400, detail="period 只能是 week 或 month")

    end_date = end or date.today()
    days = 6 if period == "week" else 29
    start_date = end_date - timedelta(days=days)

    stmt = select(CheckIn).where(
        CheckIn.date >= start_date,
        CheckIn.date <= end_date,
    )
    if user_id:
        stmt = stmt.where(CheckIn.user_id == user_id)
    rows = db.scalars(stmt.order_by(CheckIn.date)).all()

    stats = build_study_progress(list(rows), start_date, end_date)
    stats["check_in_count"] = len(rows)
    stats["period_start"] = start_date.isoformat()
    stats["period_end"] = end_date.isoformat()

    report = StudyReport(
        user_id=user_id,
        period_type=period,
        period_start=start_date,
        period_end=end_date,
        stats=stats,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "period": period,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "stats": stats,
        "generated_at": report.generated_at.isoformat(),
    }
