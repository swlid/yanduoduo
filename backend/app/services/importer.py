"""后台数据批量导入解析与落库。"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AdmissionStat, Institution, InstitutionMajor, Major


def parse_csv(content: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(content))
    return [dict(row) for row in reader]


def parse_excel(content: bytes) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("Excel 导入需要安装 openpyxl") from exc

    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    headers = [str(cell) if cell is not None else "" for cell in next(rows_iter)]
    result: list[dict[str, Any]] = []
    for row in rows_iter:
        result.append(
            {
                headers[index]: value
                for index, value in enumerate(row)
                if index < len(headers)
            }
        )
    workbook.close()
    return result


def _bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "是", "yes"}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default


def _resolve_institution(db: Session, row: dict[str, Any]) -> Institution | None:
    if row.get("institution_id"):
        return db.get(Institution, row["institution_id"])
    code = row.get("institution_code")
    if code:
        return db.scalar(select(Institution).where(Institution.code == str(code)))
    return None


def _resolve_major(db: Session, row: dict[str, Any]) -> Major | None:
    if row.get("major_id"):
        return db.get(Major, row["major_id"])
    code = row.get("major_code")
    if code:
        return db.scalar(select(Major).where(Major.code == str(code)))
    return None


def _resolve_institution_major(
    db: Session, row: dict[str, Any]
) -> InstitutionMajor | None:
    if row.get("institution_major_id"):
        return db.get(InstitutionMajor, row["institution_major_id"])
    institution = _resolve_institution(db, row)
    major = _resolve_major(db, row)
    if institution is None or major is None:
        return None
    return db.scalar(
        select(InstitutionMajor).where(
            InstitutionMajor.institution_id == institution.id,
            InstitutionMajor.major_id == major.id,
        )
    )


def import_rows(db: Session, entity_type: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if entity_type == "institution":
        return _import_institutions(db, rows)
    if entity_type == "major":
        return _import_majors(db, rows)
    if entity_type == "institution_major":
        return _import_institution_majors(db, rows)
    if entity_type == "admission_stat":
        return _import_admission_stats(db, rows)
    raise ValueError(f"不支持的实体类型：{entity_type}")


def _import_institutions(db: Session, rows: list[dict[str, Any]]) -> dict[str, Any]:
    created = 0
    updated = 0
    for row in rows:
        code = str(row.get("code", "")).strip()
        if not code or not row.get("name"):
            continue
        item = db.scalar(select(Institution).where(Institution.code == code))
        data = {
            "name": str(row["name"]),
            "short_name": str(row.get("short_name", "")),
            "province": str(row.get("province", "")),
            "city": str(row.get("city", "")),
            "level": str(row.get("level", "普通")),
            "category": str(row.get("category", "综合")),
            "is_self_draw": _bool(row.get("is_self_draw")),
            "official_url": row.get("official_url") or None,
            "logo_url": row.get("logo_url") or None,
            "tags": _json(row.get("tags"), []),
            "status": "published",
        }
        if item is None:
            db.add(Institution(code=code, **data))
            created += 1
        else:
            for key, value in data.items():
                setattr(item, key, value)
            updated += 1
    db.commit()
    return {"entity_type": "institution", "created": created, "updated": updated}


def _import_majors(db: Session, rows: list[dict[str, Any]]) -> dict[str, Any]:
    created = 0
    updated = 0
    for row in rows:
        code = str(row.get("code", "")).strip()
        if not code or not row.get("name"):
            continue
        item = db.scalar(select(Major).where(Major.code == code))
        data = {
            "name": str(row["name"]),
            "discipline_gate": str(row.get("discipline_gate", "")),
            "discipline_level1": str(row.get("discipline_level1", "")),
            "degree_type": str(row.get("degree_type", "学硕")),
            "is_cross_allowed": _bool(row.get("is_cross_allowed"), True),
            "cross_condition": row.get("cross_condition") or None,
            "apply_condition": row.get("apply_condition") or None,
            "research_directions": _json(row.get("research_directions"), []),
            "status": "published",
        }
        if item is None:
            db.add(Major(code=code, **data))
            created += 1
        else:
            for key, value in data.items():
                setattr(item, key, value)
            updated += 1
    db.commit()
    return {"entity_type": "major", "created": created, "updated": updated}


def _import_institution_majors(
    db: Session, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    created = 0
    updated = 0
    for row in rows:
        institution = _resolve_institution(db, row)
        major = _resolve_major(db, row)
        if institution is None or major is None:
            continue
        item = db.scalar(
            select(InstitutionMajor).where(
                InstitutionMajor.institution_id == institution.id,
                InstitutionMajor.major_id == major.id,
            )
        )
        data = {
            "faculty_name": str(row.get("faculty_name", "")),
            "study_mode": str(row.get("study_mode", "全日制")),
            "length": _float(row.get("length")),
            "tuition": row.get("tuition") or None,
            "scholarship": row.get("scholarship") or None,
            "exam_basic": _json(row.get("exam_basic"), {}),
            "exam_major": _json(row.get("exam_major"), {}),
            "reexam_form": _json(row.get("reexam_form"), {}),
            "additional_exam": row.get("additional_exam") or None,
            "status": "published",
        }
        if item is None:
            db.add(
                InstitutionMajor(
                    institution_id=institution.id,
                    major_id=major.id,
                    **data,
                )
            )
            created += 1
        else:
            for key, value in data.items():
                setattr(item, key, value)
            updated += 1
    db.commit()
    return {"entity_type": "institution_major", "created": created, "updated": updated}


def _import_admission_stats(
    db: Session, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    created = 0
    updated = 0
    for row in rows:
        institution_major = _resolve_institution_major(db, row)
        year = _int(row.get("year"))
        source_year = _int(row.get("source_year"), year)
        if institution_major is None or not year:
            continue
        item = db.scalar(
            select(AdmissionStat).where(
                AdmissionStat.institution_major_id == institution_major.id,
                AdmissionStat.year == year,
            )
        )
        data = {
            "plan_total": _int(row.get("plan_total")),
            "plan_unified": _int(row.get("plan_unified")),
            "recommended_count": _int(row.get("recommended_count")),
            "recommended_ratio": _float(row.get("recommended_ratio")),
            "applicant_count": _int(row.get("applicant_count")),
            "admitted_count": _int(row.get("admitted_count")),
            "report_rate": _float(row.get("report_rate")),
            "reexam_count": _int(row.get("reexam_count")),
            "reexam_admit_rate": _float(row.get("reexam_admit_rate")),
            "max_score": _float(row.get("max_score")),
            "min_score": _float(row.get("min_score")),
            "avg_score": _float(row.get("avg_score")),
            "national_line": _float(row.get("national_line")),
            "self_line": _float(row.get("self_line")),
            "college_line": _float(row.get("college_line")),
            "transfer_quota": _int(row.get("transfer_quota")),
            "metrics": _json(row.get("metrics"), {}),
            "source_url": row.get("source_url") or None,
            "source_name": str(row.get("source_name", "人工导入")),
            "source_year": source_year,
            "data_quality": str(row.get("data_quality", "official")),
            "review_status": str(row.get("review_status", "pending")),
        }
        if item is None:
            db.add(
                AdmissionStat(
                    institution_major_id=institution_major.id,
                    year=year,
                    **data,
                )
            )
            created += 1
        else:
            for key, value in data.items():
                setattr(item, key, value)
            updated += 1
    db.commit()
    return {"entity_type": "admission_stat", "created": created, "updated": updated}
