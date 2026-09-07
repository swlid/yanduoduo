"""院校查询接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Institution
from ..schemas import InstitutionOut, PageOut


router = APIRouter(prefix="/institutions", tags=["院校"])


@router.get("", response_model=PageOut)
def list_institutions(
    keyword: str | None = None,
    province: str | None = None,
    level: str | None = None,
    category: str | None = None,
    is_self_draw: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PageOut:
    conditions = [Institution.status == "published"]
    if keyword:
        pattern = f"%{keyword}%"
        conditions.append(
            or_(
                Institution.name.ilike(pattern),
                Institution.short_name.ilike(pattern),
                Institution.code.ilike(pattern),
            )
        )
    if province:
        conditions.append(Institution.province == province)
    if level:
        conditions.append(Institution.level == level)
    if category:
        conditions.append(Institution.category == category)
    if is_self_draw is not None:
        conditions.append(Institution.is_self_draw == is_self_draw)

    total = db.scalar(
        select(func.count()).select_from(Institution).where(*conditions)
    ) or 0
    rows = db.scalars(
        select(Institution)
        .where(*conditions)
        .order_by(Institution.level.desc(), Institution.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [
        InstitutionOut.model_validate(item).model_dump(mode="json") for item in rows
    ]
    return PageOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution(
    institution_id: str,
    db: Session = Depends(get_db),
) -> InstitutionOut:
    item = db.get(Institution, institution_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=404, detail="院校不存在")
    return InstitutionOut.model_validate(item)
