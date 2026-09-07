"""院校—专业组合查询、详情与对比接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import AdmissionStat, Institution, InstitutionMajor, Major
from ..schemas import (
    AdmissionStatOut,
    InstitutionMajorDetailOut,
    InstitutionMajorSummaryOut,
    InstitutionOut,
    MajorOut,
    PageOut,
)


router = APIRouter(prefix="/institution-majors", tags=["院校专业"])


def _load_statement():
    return (
        select(InstitutionMajor)
        .join(InstitutionMajor.institution)
        .join(InstitutionMajor.major)
        .options(
            selectinload(InstitutionMajor.institution),
            selectinload(InstitutionMajor.major),
            selectinload(InstitutionMajor.admission_stats),
        )
    )


def _pick_stat(
    item: InstitutionMajor, year: int | None
) -> AdmissionStat | None:
    stats = sorted(item.admission_stats, key=lambda x: x.year, reverse=True)
    if not stats:
        return None
    if year is None:
        return stats[0]
    return next((x for x in stats if x.year == year), stats[0])


def _stat_out(stat: AdmissionStat | None) -> dict | None:
    if stat is None:
        return None
    return AdmissionStatOut.model_validate(stat).model_dump(mode="json")


def _summary(item: InstitutionMajor, year: int | None) -> dict:
    return {
        "id": item.id,
        "faculty_name": item.faculty_name,
        "study_mode": item.study_mode,
        "length": float(item.length) if item.length is not None else None,
        "tuition": item.tuition,
        "scholarship": item.scholarship,
        "exam_basic": item.exam_basic,
        "exam_major": item.exam_major,
        "reexam_form": item.reexam_form,
        "additional_exam": item.additional_exam,
        "institution": InstitutionOut.model_validate(item.institution).model_dump(
            mode="json"
        ),
        "major": MajorOut.model_validate(item.major).model_dump(mode="json"),
        "latest_stat": _stat_out(_pick_stat(item, year)),
    }


def _detail(item: InstitutionMajor, year: int | None) -> dict:
    payload = _summary(item, year)
    stats = sorted(item.admission_stats, key=lambda x: x.year)
    payload["admission_stats"] = [
        AdmissionStatOut.model_validate(stat).model_dump(mode="json")
        for stat in stats
    ]
    return payload


@router.get("", response_model=PageOut)
def list_institution_majors(
    keyword: str | None = None,
    institution_id: str | None = None,
    major_id: str | None = None,
    province: str | None = None,
    level: str | None = None,
    category: str | None = None,
    discipline_gate: str | None = None,
    degree_type: str | None = None,
    study_mode: str | None = None,
    is_self_draw: bool | None = None,
    year: int | None = Query(2025, ge=2000, le=2100),
    min_avg_score: float | None = Query(None, ge=0, le=750),
    max_avg_score: float | None = Query(None, ge=0, le=750),
    min_report_rate: float | None = Query(None, ge=0),
    max_report_rate: float | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PageOut:
    stmt = _load_statement()
    conditions = [InstitutionMajor.status == "published"]

    if keyword:
        pattern = f"%{keyword}%"
        conditions.append(
            or_(
                Institution.name.ilike(pattern),
                Institution.short_name.ilike(pattern),
                Major.name.ilike(pattern),
                Major.discipline_level1.ilike(pattern),
                InstitutionMajor.faculty_name.ilike(pattern),
            )
        )
    if institution_id:
        conditions.append(InstitutionMajor.institution_id == institution_id)
    if major_id:
        conditions.append(InstitutionMajor.major_id == major_id)
    if province:
        conditions.append(Institution.province == province)
    if level:
        conditions.append(Institution.level == level)
    if category:
        conditions.append(Institution.category == category)
    if discipline_gate:
        conditions.append(Major.discipline_gate == discipline_gate)
    if degree_type:
        conditions.append(Major.degree_type == degree_type)
    if study_mode:
        conditions.append(InstitutionMajor.study_mode == study_mode)
    if is_self_draw is not None:
        conditions.append(Institution.is_self_draw == is_self_draw)

    rows = list(db.scalars(stmt.where(*conditions)).all())

    def passes_stat_filter(item: InstitutionMajor) -> bool:
        stat = _pick_stat(item, year)
        if stat is None:
            return True
        if min_avg_score is not None and (
            stat.avg_score is None or float(stat.avg_score) < min_avg_score
        ):
            return False
        if max_avg_score is not None and (
            stat.avg_score is None or float(stat.avg_score) > max_avg_score
        ):
            return False
        if min_report_rate is not None and (
            stat.report_rate is None or float(stat.report_rate) < min_report_rate
        ):
            return False
        if max_report_rate is not None and (
            stat.report_rate is None or float(stat.report_rate) > max_report_rate
        ):
            return False
        return True

    filtered = [item for item in rows if passes_stat_filter(item)]
    total = len(filtered)
    start = (page - 1) * page_size
    page_rows = filtered[start : start + page_size]
    items = [_summary(item, year) for item in page_rows]
    return PageOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/compare", response_model=dict)
def compare_institution_majors(
    ids: str = Query(..., description="逗号分隔的院校专业 ID，最多 4 个"),
    year: int = Query(2025, ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> dict:
    id_list = [item.strip() for item in ids.split(",") if item.strip()][:4]
    if not id_list:
        raise HTTPException(status_code=400, detail="ids 不能为空")

    stmt = (
        _load_statement()
        .where(InstitutionMajor.id.in_(id_list))
    )
    rows = list(db.scalars(stmt).all())
    ordered = {item.id: item for item in rows}
    items = [
        _detail(ordered[item_id], year)
        for item_id in id_list
        if item_id in ordered
    ]
    return {
        "items": items,
        "count": len(items),
        "year": year,
        "missing_ids": [item_id for item_id in id_list if item_id not in ordered],
    }


@router.get("/{item_id}", response_model=InstitutionMajorDetailOut)
def get_institution_major(
    item_id: str,
    year: int = Query(2025, ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> InstitutionMajorDetailOut:
    stmt = _load_statement().where(InstitutionMajor.id == item_id)
    item = db.scalar(stmt)
    if item is None or item.status != "published":
        raise HTTPException(status_code=404, detail="院校专业组合不存在")
    return InstitutionMajorDetailOut.model_validate(_detail(item, year))
