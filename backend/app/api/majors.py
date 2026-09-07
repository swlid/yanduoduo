"""专业目录查询接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Major
from ..schemas import MajorOut, PageOut


router = APIRouter(prefix="/majors", tags=["专业"])


@router.get("", response_model=PageOut)
def list_majors(
    keyword: str | None = None,
    discipline_gate: str | None = None,
    degree_type: str | None = None,
    is_cross_allowed: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PageOut:
    conditions = [Major.status == "published"]
    if keyword:
        pattern = f"%{keyword}%"
        conditions.append(
            or_(
                Major.name.ilike(pattern),
                Major.code.ilike(pattern),
                Major.discipline_level1.ilike(pattern),
            )
        )
    if discipline_gate:
        conditions.append(Major.discipline_gate == discipline_gate)
    if degree_type:
        conditions.append(Major.degree_type == degree_type)
    if is_cross_allowed is not None:
        conditions.append(Major.is_cross_allowed == is_cross_allowed)

    total = db.scalar(
        select(func.count()).select_from(Major).where(*conditions)
    ) or 0
    rows = db.scalars(
        select(Major)
        .where(*conditions)
        .order_by(Major.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [MajorOut.model_validate(item).model_dump(mode="json") for item in rows]
    return PageOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{major_id}", response_model=MajorOut)
def get_major(major_id: str, db: Session = Depends(get_db)) -> MajorOut:
    item = db.get(Major, major_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=404, detail="专业不存在")
    return MajorOut.model_validate(item)
