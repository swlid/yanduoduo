"""择校梯度推荐规则引擎。

首版不使用 AI，采用可解释的规则：估分与近 3 年平均分的差值 + 报录比竞争修正。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import AdmissionStat, Assessment, InstitutionMajor, Recommendation


TIER_LIMIT = 3


def build_profile(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "undergrad_major": payload["undergrad_major"],
        "target_provinces": payload.get("target_provinces") or [],
        "estimated_total_score": payload["estimated_total_score"],
        "is_cross_major": bool(payload.get("is_cross_major")),
        "degree_type": payload.get("degree_type", "不限"),
        "target_level": payload.get("target_level"),
    }


def _latest_stat(item: InstitutionMajor) -> AdmissionStat | None:
    stats = sorted(item.admission_stats, key=lambda x: x.year, reverse=True)
    return stats[0] if stats else None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _classify_tier(gap: float, report_rate: float | None) -> str:
    adjusted = gap
    if report_rate is not None:
        if report_rate >= 20:
            adjusted -= 5
        elif report_rate < 8:
            adjusted += 5
    if adjusted < -5:
        return "冲刺"
    if adjusted <= 6:
        return "稳妥"
    return "保底"


def _probability(gap: float, report_rate: float | None) -> float:
    value = 50 + gap * 1.8
    if report_rate is not None:
        value -= (report_rate - 10) * 0.8
    return round(max(5.0, min(95.0, value)), 2)


def _reason_text(tier: str, gap: float, report_rate: float | None) -> str:
    direction = "低于" if gap < 0 else "高于"
    competition = (
        f"报录比 {report_rate:.1f}，竞争较激烈"
        if report_rate and report_rate >= 15
        else f"报录比 {report_rate:.1f}"
        if report_rate is not None
        else "竞争数据缺失"
    )
    if tier == "冲刺":
        return f"你的估分{direction}近 3 年平均录取分约 {abs(gap):.0f} 分，属于冲刺目标；{competition}。"
    if tier == "稳妥":
        return f"你的估分与近 3 年平均录取分差距约 {abs(gap):.0f} 分，属于稳妥目标；{competition}。"
    return f"你的估分{direction}近 3 年平均录取分约 {abs(gap):.0f} 分，属于保底目标；{competition}。"


def generate_recommendations(
    db: Session,
    assessment_id: str,
    payload: dict[str, Any],
) -> list[Recommendation]:
    """基于 Mock 数据生成冲刺/稳妥/保底三梯度推荐。"""
    estimated = int(payload["estimated_total_score"])
    target_provinces = set(payload.get("target_provinces") or [])
    degree_type = payload.get("degree_type", "不限")
    is_cross_major = bool(payload.get("is_cross_major"))
    target_level = payload.get("target_level")

    stmt = (
        select(InstitutionMajor)
        .options(
            selectinload(InstitutionMajor.institution),
            selectinload(InstitutionMajor.major),
            selectinload(InstitutionMajor.admission_stats),
        )
        .where(InstitutionMajor.status == "published")
    )

    grouped: dict[str, list[Recommendation]] = {
        "冲刺": [],
        "稳妥": [],
        "保底": [],
    }

    for item in db.scalars(stmt).all():
        stat = _latest_stat(item)
        if stat is None or stat.avg_score is None:
            continue
        if target_provinces and item.institution.province not in target_provinces:
            continue
        if degree_type != "不限" and item.major.degree_type != degree_type:
            continue
        if is_cross_major and not item.major.is_cross_allowed:
            continue
        if target_level and item.institution.level != target_level:
            continue

        avg_score = float(stat.avg_score)
        report_rate = _to_float(stat.report_rate)
        gap = estimated - avg_score
        tier = _classify_tier(gap, report_rate)
        probability = _probability(gap, report_rate)
        score = round(100 - min(abs(gap) * 1.2, 60) - (report_rate or 0) * 0.5, 2)

        grouped[tier].append(
            Recommendation(
                assessment_id=assessment_id,
                institution_major_id=item.id,
                tier=tier,
                score=Decimal(str(max(0, score))),
                probability=Decimal(str(probability)),
                reason={
                    "text": _reason_text(tier, gap, report_rate),
                    "gap": round(gap, 1),
                    "estimated_score": estimated,
                    "avg_score": round(avg_score, 1),
                    "report_rate": report_rate,
                    "reexam_admit_rate": _to_float(stat.reexam_admit_rate),
                    "trend": (stat.metrics or {}).get("trend", "未知"),
                },
                data_refs={
                    "source_name": stat.source_name,
                    "source_year": stat.source_year,
                    "data_quality": stat.data_quality,
                    "year": stat.year,
                },
            )
        )

    recommendations: list[Recommendation] = []
    for tier in ("冲刺", "稳妥", "保底"):
        candidates = sorted(
            grouped[tier],
            key=lambda x: float(x.probability),
            reverse=True,
        )
        recommendations.extend(candidates[:TIER_LIMIT])
    return recommendations
