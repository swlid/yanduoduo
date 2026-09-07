"""资讯文章与用户纠错公开接口。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Article, DataCorrection
from ..schemas import ArticleOut, CorrectionCreate, CorrectionOut


router = APIRouter(tags=["内容"])


@router.get("/articles", response_model=list[ArticleOut])
def list_articles(
    category: str | None = None,
    db: Session = Depends(get_db),
) -> list[ArticleOut]:
    stmt = select(Article).where(Article.status == "published")
    if category:
        stmt = stmt.where(Article.category == category)
    rows = db.scalars(stmt.order_by(Article.published_at.desc())).all()
    return [ArticleOut.model_validate(row) for row in rows]


@router.get("/articles/{article_id}", response_model=ArticleOut)
def get_article(article_id: str, db: Session = Depends(get_db)) -> ArticleOut:
    item = db.get(Article, article_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=404, detail="文章不存在")
    return ArticleOut.model_validate(item)


@router.post("/corrections", response_model=CorrectionOut, status_code=201)
def create_correction(
    payload: CorrectionCreate,
    db: Session = Depends(get_db),
) -> CorrectionOut:
    item = DataCorrection(
        user_id=payload.user_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        field_name=payload.field_name,
        original_value=payload.original_value,
        suggested_value=payload.suggested_value,
        note=payload.note,
        status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return CorrectionOut.model_validate(item)
