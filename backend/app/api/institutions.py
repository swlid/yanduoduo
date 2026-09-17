"""院校查询接口（列表 / 分面 / 详情概览）。

本模块只读院校与「院校-专业-招录」汇总信息，不改动任何数据；
所有原有字段与参数保持向后兼容。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AdmissionStat, Institution, InstitutionMajor
from ..schemas import (
    FacetItem,
    InstitutionFacetsOut,
    InstitutionListItemOut,
    InstitutionOut,
    InstitutionOverviewOut,
    PageOut,
)


router = APIRouter(prefix="/institutions", tags=["院校"])

LEVEL_ORDER = ["985", "211", "双一流", "普通"]
LEVEL_RANK = {name: len(LEVEL_ORDER) - index for index, name in enumerate(LEVEL_ORDER)}
NO_VALUE = {"", "暂无", "未知"}


def _official_institution_subquery():
    """有官方已审核招录数据的院校 id 子查询。"""
    return (
        select(InstitutionMajor.institution_id)
        .join(AdmissionStat, AdmissionStat.institution_major_id == InstitutionMajor.id)
        .where(
            InstitutionMajor.status == "published",
            AdmissionStat.review_status == "approved",
            AdmissionStat.data_quality == "official",
        )
        .distinct()
    )


def _combo_counts(db: Session, ids: list[str]) -> dict[str, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(InstitutionMajor.institution_id, func.count(InstitutionMajor.id))
        .where(
            InstitutionMajor.institution_id.in_(ids),
            InstitutionMajor.status == "published",
        )
        .group_by(InstitutionMajor.institution_id)
    ).all()
    return {institution_id: int(count) for institution_id, count in rows}


def _official_stats(db: Session, ids: list[str]) -> dict[str, dict[str, set]]:
    """返回 {院校 id: {"combo_ids": set, "years": set}}（仅官方已审核数据）。"""
    if not ids:
        return {}
    rows = db.execute(
        select(
            InstitutionMajor.institution_id,
            InstitutionMajor.id,
            AdmissionStat.year,
        )
        .join(AdmissionStat, AdmissionStat.institution_major_id == InstitutionMajor.id)
        .where(
            InstitutionMajor.institution_id.in_(ids),
            InstitutionMajor.status == "published",
            AdmissionStat.review_status == "approved",
            AdmissionStat.data_quality == "official",
        )
        .distinct()
    ).all()
    data: dict[str, dict[str, set]] = {}
    for institution_id, combo_id, year in rows:
        entry = data.setdefault(institution_id, {"combo_ids": set(), "years": set()})
        entry["combo_ids"].add(combo_id)
        entry["years"].add(int(year))
    return data


def _latest_years(db: Session, ids: list[str]) -> dict[str, int]:
    """最近有已审核数据的年份（不限 official/mock）。"""
    if not ids:
        return {}
    rows = db.execute(
        select(InstitutionMajor.institution_id, func.max(AdmissionStat.year))
        .join(AdmissionStat, AdmissionStat.institution_major_id == InstitutionMajor.id)
        .where(
            InstitutionMajor.institution_id.in_(ids),
            InstitutionMajor.status == "published",
            AdmissionStat.review_status == "approved",
        )
        .group_by(InstitutionMajor.institution_id)
    ).all()
    return {
        institution_id: int(year)
        for institution_id, year in rows
        if year is not None
    }


def _attach_metrics(db: Session, rows: list[Institution]) -> list[dict]:
    ids = [item.id for item in rows]
    combos = _combo_counts(db, ids)
    official = _official_stats(db, ids)
    latest = _latest_years(db, ids)

    items: list[dict] = []
    for item in rows:
        official_entry = official.get(item.id, {})
        years = sorted(official_entry.get("years", set()), reverse=True)
        payload = InstitutionListItemOut.model_validate(item).model_dump(mode="json")
        payload.update(
            {
                "combo_count": combos.get(item.id, 0),
                "official_combo_count": len(official_entry.get("combo_ids", set())),
                "official_years": years,
                "has_official_data": len(official_entry.get("combo_ids", set())) > 0,
                "latest_data_year": latest.get(item.id),
            }
        )
        items.append(payload)
    return items


@router.get("", response_model=PageOut)
def list_institutions(
    keyword: str | None = None,
    province: str | None = None,
    level: str | None = None,
    category: str | None = None,
    is_self_draw: bool | None = None,
    has_data: bool | None = Query(
        None, description="true=仅有官方已审核数据的院校；false=仅无官方数据的院校"
    ),
    sort: str = Query("default", description="default / has_data / name"),
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

    official_subquery = _official_institution_subquery()
    if has_data is True:
        conditions.append(Institution.id.in_(official_subquery))
    elif has_data is False:
        conditions.append(Institution.id.not_in(official_subquery))

    level_rank = case(LEVEL_RANK, value=Institution.level, else_=0)
    if sort == "name":
        ordering = [Institution.name]
    elif sort == "has_data":
        has_official = case((Institution.id.in_(official_subquery), 1), else_=0)
        ordering = [has_official.desc(), level_rank.desc(), Institution.name]
    else:
        ordering = [level_rank.desc(), Institution.name]

    total = db.scalar(
        select(func.count()).select_from(Institution).where(*conditions)
    ) or 0
    rows = list(
        db.scalars(
            select(Institution)
            .where(*conditions)
            .order_by(*ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PageOut(
        items=_attach_metrics(db, rows),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/facets", response_model=InstitutionFacetsOut)
def get_institution_facets(db: Session = Depends(get_db)) -> InstitutionFacetsOut:
    """供前端动态生成筛选项（省份/层次/类型计数）。"""
    published = Institution.status == "published"
    total = db.scalar(
        select(func.count()).select_from(Institution).where(published)
    ) or 0

    province_rows = db.execute(
        select(Institution.province, func.count(Institution.id))
        .where(published, Institution.province.not_in(NO_VALUE))
        .group_by(Institution.province)
        .order_by(func.count(Institution.id).desc(), Institution.province)
    ).all()
    provinces = [
        FacetItem(value=value, count=int(count)) for value, count in province_rows
    ]

    level_rows = db.execute(
        select(Institution.level, func.count(Institution.id))
        .where(published, Institution.level.not_in(NO_VALUE))
        .group_by(Institution.level)
    ).all()
    level_counts = {value: int(count) for value, count in level_rows}
    levels = [
        FacetItem(value=name, count=level_counts[name])
        for name in LEVEL_ORDER
        if level_counts.get(name)
    ]

    category_rows = db.execute(
        select(Institution.category, func.count(Institution.id))
        .where(published, Institution.category.not_in(NO_VALUE))
        .group_by(Institution.category)
        .order_by(func.count(Institution.id).desc(), Institution.category)
    ).all()
    categories = [
        FacetItem(value=value, count=int(count)) for value, count in category_rows
    ]

    self_draw_count = db.scalar(
        select(func.count())
        .select_from(Institution)
        .where(published, Institution.is_self_draw.is_(True))
    ) or 0
    has_data_count = db.scalar(
        select(func.count(func.distinct(InstitutionMajor.institution_id)))
        .select_from(InstitutionMajor)
        .join(AdmissionStat, AdmissionStat.institution_major_id == InstitutionMajor.id)
        .where(
            InstitutionMajor.status == "published",
            AdmissionStat.review_status == "approved",
            AdmissionStat.data_quality == "official",
        )
    ) or 0

    return InstitutionFacetsOut(
        provinces=provinces,
        levels=levels,
        categories=categories,
        self_draw_count=int(self_draw_count),
        has_data_count=int(has_data_count),
        total=int(total),
    )


@router.get("/{institution_id}/overview", response_model=InstitutionOverviewOut)
def get_institution_overview(
    institution_id: str,
    db: Session = Depends(get_db),
) -> InstitutionOverviewOut:
    item = db.get(Institution, institution_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=404, detail="院校不存在")

    payload = _attach_metrics(db, [item])[0]
    latest_updated_at = db.scalar(
        select(func.max(AdmissionStat.updated_at))
        .select_from(AdmissionStat)
        .join(InstitutionMajor, AdmissionStat.institution_major_id == InstitutionMajor.id)
        .where(
            InstitutionMajor.institution_id == item.id,
            InstitutionMajor.status == "published",
            AdmissionStat.review_status == "approved",
        )
    )
    payload["latest_updated_at"] = latest_updated_at
    return InstitutionOverviewOut.model_validate(payload)


@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution(
    institution_id: str,
    db: Session = Depends(get_db),
) -> InstitutionOut:
    item = db.get(Institution, institution_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=404, detail="院校不存在")
    return InstitutionOut.model_validate(item)
