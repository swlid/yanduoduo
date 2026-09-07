"""择校测评与梯度推荐接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Assessment, InstitutionMajor, Recommendation
from ..schemas import (
    AdmissionStatOut,
    AssessmentCreate,
    AssessmentDetailOut,
    AssessmentOut,
    InstitutionMajorSummaryOut,
    InstitutionOut,
    MajorOut,
    RecommendationOut,
)
from ..services.recommender import build_profile, generate_recommendations


router = APIRouter(prefix="/assessments", tags=["择校测评"])


def _latest_stat(item: InstitutionMajor):
    stats = sorted(item.admission_stats, key=lambda x: x.year, reverse=True)
    return stats[0] if stats else None


def _summary(item: InstitutionMajor) -> dict:
    stat = _latest_stat(item)
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
        "latest_stat": AdmissionStatOut.model_validate(stat).model_dump(mode="json")
        if stat
        else None,
    }


def _recommendation_out(rec: Recommendation) -> dict:
    return {
        "id": rec.id,
        "assessment_id": rec.assessment_id,
        "institution_major_id": rec.institution_major_id,
        "tier": rec.tier,
        "score": float(rec.score),
        "probability": float(rec.probability),
        "reason": rec.reason,
        "data_refs": rec.data_refs,
        "institution_major": _summary(rec.institution_major),
    }


def _detail(assessment: Assessment) -> dict:
    return {
        "id": assessment.id,
        "undergrad_major": assessment.undergrad_major,
        "target_provinces": assessment.target_provinces,
        "estimated_total_score": assessment.estimated_total_score,
        "is_cross_major": assessment.is_cross_major,
        "degree_type": assessment.degree_type,
        "target_level": assessment.target_level,
        "profile": assessment.profile,
        "recommendations": [
            _recommendation_out(rec) for rec in assessment.recommendations
        ],
    }


@router.post("", response_model=AssessmentDetailOut, status_code=201)
def create_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
) -> AssessmentDetailOut:
    profile = build_profile(payload.model_dump())
    assessment = Assessment(
        user_id=None,
        undergrad_major=payload.undergrad_major,
        target_provinces=payload.target_provinces,
        estimated_total_score=payload.estimated_total_score,
        is_cross_major=payload.is_cross_major,
        degree_type=payload.degree_type,
        target_level=payload.target_level,
        profile=profile,
    )
    db.add(assessment)
    db.flush()

    recommendations = generate_recommendations(db, assessment.id, profile)
    db.add_all(recommendations)
    db.commit()

    stmt = (
        select(Assessment)
        .where(Assessment.id == assessment.id)
        .options(
            selectinload(Assessment.recommendations).selectinload(
                Recommendation.institution_major
            ),
            selectinload(Assessment.recommendations).selectinload(
                Recommendation.institution_major
            ).selectinload(InstitutionMajor.institution),
            selectinload(Assessment.recommendations).selectinload(
                Recommendation.institution_major
            ).selectinload(InstitutionMajor.major),
            selectinload(Assessment.recommendations).selectinload(
                Recommendation.institution_major
            ).selectinload(InstitutionMajor.admission_stats),
        )
    )
    refreshed = db.scalar(stmt)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="测评结果生成失败")
    return AssessmentDetailOut.model_validate(_detail(refreshed))


@router.get("/{assessment_id}", response_model=AssessmentDetailOut)
def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
) -> AssessmentDetailOut:
    stmt = (
        select(Assessment)
        .where(Assessment.id == assessment_id)
        .options(
            selectinload(Assessment.recommendations).selectinload(
                Recommendation.institution_major
            ),
            selectinload(Assessment.recommendations).selectinload(
                Recommendation.institution_major
            ).selectinload(InstitutionMajor.institution),
            selectinload(Assessment.recommendations).selectinload(
                Recommendation.institution_major
            ).selectinload(InstitutionMajor.major),
            selectinload(Assessment.recommendations).selectinload(
                Recommendation.institution_major
            ).selectinload(InstitutionMajor.admission_stats),
        )
    )
    assessment = db.scalar(stmt)
    if assessment is None:
        raise HTTPException(status_code=404, detail="测评记录不存在")
    return AssessmentDetailOut.model_validate(_detail(assessment))


@router.get(
    "/{assessment_id}/recommendations",
    response_model=list[RecommendationOut],
)
def list_recommendations(
    assessment_id: str,
    db: Session = Depends(get_db),
) -> list[RecommendationOut]:
    stmt = (
        select(Recommendation)
        .where(Recommendation.assessment_id == assessment_id)
        .options(
            selectinload(Recommendation.institution_major).selectinload(
                InstitutionMajor.institution
            ),
            selectinload(Recommendation.institution_major).selectinload(
                InstitutionMajor.major
            ),
            selectinload(Recommendation.institution_major).selectinload(
                InstitutionMajor.admission_stats
            ),
        )
    )
    rows = db.scalars(stmt).all()
    return [RecommendationOut.model_validate(_recommendation_out(rec)) for rec in rows]
