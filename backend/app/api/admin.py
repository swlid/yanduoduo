"""管理后台数据维护接口（MVP 无鉴权，生产需加权限）。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import (
    AdmissionStat,
    Article,
    DataCorrection,
    Institution,
    InstitutionMajor,
    Major,
)
from ..schemas import (
    AdmissionStatCreate,
    AdmissionStatOut,
    AdmissionStatReview,
    AdmissionStatUpdate,
    ArticleCreate,
    ArticleOut,
    ArticleUpdate,
    CorrectionOut,
    CorrectionReview,
    InstitutionCreate,
    InstitutionMajorCreate,
    InstitutionMajorDetailOut,
    InstitutionMajorUpdate,
    InstitutionOut,
    InstitutionUpdate,
    MajorCreate,
    MajorOut,
    MajorUpdate,
)
from ..services.importer import import_rows, parse_csv, parse_excel


router = APIRouter(prefix="/admin", tags=["管理后台"])


def _apply_updates(item, data: dict):
    for key, value in data.items():
        if value is not None:
            setattr(item, key, value)


def _load_institution_major(db: Session, item_id: str) -> InstitutionMajor | None:
    return db.scalar(
        select(InstitutionMajor)
        .where(InstitutionMajor.id == item_id)
        .options(
            selectinload(InstitutionMajor.institution),
            selectinload(InstitutionMajor.major),
            selectinload(InstitutionMajor.admission_stats),
        )
    )


def _im_detail(item: InstitutionMajor) -> dict:
    stats = sorted(item.admission_stats, key=lambda x: x.year, reverse=True)
    latest = stats[0] if stats else None
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
        "latest_stat": AdmissionStatOut.model_validate(latest).model_dump(mode="json")
        if latest
        else None,
        "admission_stats": [
            AdmissionStatOut.model_validate(s).model_dump(mode="json")
            for s in stats
        ],
    }


@router.post("/institutions", response_model=InstitutionOut, status_code=201)
def create_institution(
    payload: InstitutionCreate,
    db: Session = Depends(get_db),
) -> InstitutionOut:
    item = Institution(**payload.model_dump(), status="published")
    db.add(item)
    db.commit()
    db.refresh(item)
    return InstitutionOut.model_validate(item)


@router.put("/institutions/{item_id}", response_model=InstitutionOut)
def update_institution(
    item_id: str,
    payload: InstitutionUpdate,
    db: Session = Depends(get_db),
) -> InstitutionOut:
    item = db.get(Institution, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="院校不存在")
    _apply_updates(item, payload.model_dump())
    db.commit()
    db.refresh(item)
    return InstitutionOut.model_validate(item)


@router.delete("/institutions/{item_id}", response_model=dict)
def archive_institution(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(Institution, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="院校不存在")
    item.status = "archived"
    db.commit()
    return {"deleted": True, "id": item_id}


@router.post("/majors", response_model=MajorOut, status_code=201)
def create_major(payload: MajorCreate, db: Session = Depends(get_db)) -> MajorOut:
    item = Major(**payload.model_dump(), status="published")
    db.add(item)
    db.commit()
    db.refresh(item)
    return MajorOut.model_validate(item)


@router.put("/majors/{item_id}", response_model=MajorOut)
def update_major(
    item_id: str,
    payload: MajorUpdate,
    db: Session = Depends(get_db),
) -> MajorOut:
    item = db.get(Major, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="专业不存在")
    _apply_updates(item, payload.model_dump())
    db.commit()
    db.refresh(item)
    return MajorOut.model_validate(item)


@router.delete("/majors/{item_id}", response_model=dict)
def archive_major(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(Major, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="专业不存在")
    item.status = "archived"
    db.commit()
    return {"deleted": True, "id": item_id}


@router.post(
    "/institution-majors",
    response_model=InstitutionMajorDetailOut,
    status_code=201,
)
def create_institution_major(
    payload: InstitutionMajorCreate,
    db: Session = Depends(get_db),
) -> InstitutionMajorDetailOut:
    item = InstitutionMajor(**payload.model_dump(), status="published")
    db.add(item)
    db.commit()
    refreshed = _load_institution_major(db, item.id)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="创建失败")
    return InstitutionMajorDetailOut.model_validate(_im_detail(refreshed))


@router.put(
    "/institution-majors/{item_id}",
    response_model=InstitutionMajorDetailOut,
)
def update_institution_major(
    item_id: str,
    payload: InstitutionMajorUpdate,
    db: Session = Depends(get_db),
) -> InstitutionMajorDetailOut:
    item = _load_institution_major(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="院校专业组合不存在")
    _apply_updates(item, payload.model_dump())
    db.commit()
    refreshed = _load_institution_major(db, item_id)
    return InstitutionMajorDetailOut.model_validate(_im_detail(refreshed))


@router.delete("/institution-majors/{item_id}", response_model=dict)
def archive_institution_major(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(InstitutionMajor, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="院校专业组合不存在")
    item.status = "archived"
    db.commit()
    return {"deleted": True, "id": item_id}


@router.post("/admission-stats", response_model=AdmissionStatOut, status_code=201)
def create_admission_stat(
    payload: AdmissionStatCreate,
    db: Session = Depends(get_db),
) -> AdmissionStatOut:
    item = AdmissionStat(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return AdmissionStatOut.model_validate(item)


@router.put("/admission-stats/{item_id}", response_model=AdmissionStatOut)
def update_admission_stat(
    item_id: str,
    payload: AdmissionStatUpdate,
    db: Session = Depends(get_db),
) -> AdmissionStatOut:
    item = db.get(AdmissionStat, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="招录数据不存在")
    _apply_updates(item, payload.model_dump())
    db.commit()
    db.refresh(item)
    return AdmissionStatOut.model_validate(item)


@router.delete("/admission-stats/{item_id}", response_model=dict)
def delete_admission_stat(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(AdmissionStat, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="招录数据不存在")
    db.delete(item)
    db.commit()
    return {"deleted": True, "id": item_id}


@router.get("/admission-stats", response_model=dict)
def list_admission_stats(
    review_status: str | None = None,
    data_quality: str | None = None,
    year: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(AdmissionStat).options(
        selectinload(AdmissionStat.institution_major).selectinload(
            InstitutionMajor.institution
        ),
        selectinload(AdmissionStat.institution_major).selectinload(
            InstitutionMajor.major
        ),
    )
    conditions = []
    if review_status:
        conditions.append(AdmissionStat.review_status == review_status)
    if data_quality:
        conditions.append(AdmissionStat.data_quality == data_quality)
    if year:
        conditions.append(AdmissionStat.year == year)
    rows = list(
        db.scalars(stmt.where(*conditions).order_by(AdmissionStat.created_at.desc())).all()
    )
    total = len(rows)
    page_rows = rows[(page - 1) * page_size : page * page_size]
    items = []
    for stat in page_rows:
        payload = AdmissionStatOut.model_validate(stat).model_dump(mode="json")
        im = stat.institution_major
        payload["institution_name"] = im.institution.name
        payload["major_name"] = im.major.name
        payload["major_code"] = im.major.code
        payload["faculty_name"] = im.faculty_name
        items.append(payload)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/admission-stats/{item_id}/review", response_model=AdmissionStatOut)
def review_admission_stat(
    item_id: str,
    payload: AdmissionStatReview,
    db: Session = Depends(get_db),
) -> AdmissionStatOut:
    item = db.get(AdmissionStat, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="招录数据不存在")
    item.review_status = payload.review_status
    item.reviewed_by = payload.reviewed_by
    item.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return AdmissionStatOut.model_validate(item)


@router.post("/import", response_model=dict)
async def import_data(
    entity_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    content = await file.read()
    filename = (file.filename or "").lower()
    try:
        if filename.endswith(".csv"):
            rows = parse_csv(content.decode("utf-8-sig"))
        elif filename.endswith((".xlsx", ".xls")):
            rows = parse_excel(content)
        else:
            raise HTTPException(status_code=400, detail="仅支持 CSV 或 Excel 文件")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="文件编码不是 UTF-8") from exc

    try:
        summary = import_rows(db, entity_type, rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"file": file.filename, "rows": len(rows), **summary}


@router.get("/corrections", response_model=list[CorrectionOut])
def list_corrections(
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[CorrectionOut]:
    stmt = select(DataCorrection)
    if status:
        stmt = stmt.where(DataCorrection.status == status)
    rows = db.scalars(stmt.order_by(DataCorrection.created_at.desc())).all()
    return [CorrectionOut.model_validate(row) for row in rows]


@router.post("/corrections/{item_id}/review", response_model=CorrectionOut)
def review_correction(
    item_id: str,
    payload: CorrectionReview,
    db: Session = Depends(get_db),
) -> CorrectionOut:
    item = db.get(DataCorrection, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="纠错记录不存在")
    item.status = payload.status
    item.reviewed_by = payload.reviewed_by
    item.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return CorrectionOut.model_validate(item)


@router.post("/articles", response_model=ArticleOut, status_code=201)
def create_article(
    payload: ArticleCreate,
    db: Session = Depends(get_db),
) -> ArticleOut:
    item = Article(**payload.model_dump())
    if item.status == "published" and item.published_at is None:
        item.published_at = datetime.now(timezone.utc)
    db.add(item)
    db.commit()
    db.refresh(item)
    return ArticleOut.model_validate(item)


@router.put("/articles/{item_id}", response_model=ArticleOut)
def update_article(
    item_id: str,
    payload: ArticleUpdate,
    db: Session = Depends(get_db),
) -> ArticleOut:
    item = db.get(Article, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    _apply_updates(item, payload.model_dump())
    if item.status == "published" and item.published_at is None:
        item.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return ArticleOut.model_validate(item)


@router.delete("/articles/{item_id}", response_model=dict)
def delete_article(item_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(Article, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(item)
    db.commit()
    return {"deleted": True, "id": item_id}
