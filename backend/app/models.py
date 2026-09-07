"""核心数据模型。

遵循「院校—专业—年度—指标」骨架；招录事实表每年一行，
`metrics` 承载未来新增指标。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Institution(TimestampMixin, Base):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    short_name: Mapped[str] = mapped_column(String(40), default="")
    province: Mapped[str] = mapped_column(String(40), index=True)
    city: Mapped[str] = mapped_column(String(40), index=True)
    level: Mapped[str] = mapped_column(String(20), index=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    is_self_draw: Mapped[bool] = mapped_column(Boolean, default=False)
    official_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)

    institution_majors: Mapped[list["InstitutionMajor"]] = relationship(
        back_populates="institution", cascade="all, delete-orphan"
    )


class Major(TimestampMixin, Base):
    __tablename__ = "majors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    discipline_gate: Mapped[str] = mapped_column(String(20), index=True)
    discipline_level1: Mapped[str] = mapped_column(String(80), index=True)
    degree_type: Mapped[str] = mapped_column(String(20), index=True)
    is_cross_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    cross_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_directions: Mapped[list[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)

    institution_majors: Mapped[list["InstitutionMajor"]] = relationship(
        back_populates="major", cascade="all, delete-orphan"
    )


class InstitutionMajor(TimestampMixin, Base):
    __tablename__ = "institution_majors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    institution_id: Mapped[str] = mapped_column(
        ForeignKey("institutions.id"), index=True
    )
    major_id: Mapped[str] = mapped_column(ForeignKey("majors.id"), index=True)
    faculty_name: Mapped[str] = mapped_column(String(160), default="")
    study_mode: Mapped[str] = mapped_column(String(20), default="全日制", index=True)
    length: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    tuition: Mapped[str | None] = mapped_column(Text, nullable=True)
    scholarship: Mapped[str | None] = mapped_column(Text, nullable=True)
    exam_basic: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    exam_major: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reexam_form: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    additional_exam: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)

    institution: Mapped["Institution"] = relationship(back_populates="institution_majors")
    major: Mapped["Major"] = relationship(back_populates="institution_majors")
    admission_stats: Mapped[list["AdmissionStat"]] = relationship(
        back_populates="institution_major", cascade="all, delete-orphan"
    )


class AdmissionStat(TimestampMixin, Base):
    __tablename__ = "admission_stats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    institution_major_id: Mapped[str] = mapped_column(
        ForeignKey("institution_majors.id"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, index=True)
    plan_total: Mapped[int] = mapped_column(Integer, default=0)
    plan_unified: Mapped[int] = mapped_column(Integer, default=0)
    recommended_count: Mapped[int] = mapped_column(Integer, default=0)
    recommended_ratio: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    applicant_count: Mapped[int] = mapped_column(Integer, default=0)
    admitted_count: Mapped[int] = mapped_column(Integer, default=0)
    report_rate: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    reexam_count: Mapped[int] = mapped_column(Integer, default=0)
    reexam_admit_rate: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    max_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    min_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    avg_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    national_line: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    self_line: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    college_line: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    transfer_quota: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(120), default="Mock 示例数据")
    source_year: Mapped[int] = mapped_column(Integer)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    data_quality: Mapped[str] = mapped_column(String(20), default="mock", index=True)
    review_status: Mapped[str] = mapped_column(String(20), default="approved", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    institution_major: Mapped["InstitutionMajor"] = relationship(
        back_populates="admission_stats"
    )


class Assessment(TimestampMixin, Base):
    """择校基础测评与个人画像。"""

    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    undergrad_major: Mapped[str] = mapped_column(String(120))
    target_provinces: Mapped[list[Any]] = mapped_column(JSON, default=list)
    estimated_total_score: Mapped[int] = mapped_column(Integer)
    is_cross_major: Mapped[bool] = mapped_column(Boolean, default=False)
    degree_type: Mapped[str] = mapped_column(String(20), default="不限")
    target_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Recommendation(TimestampMixin, Base):
    """梯度推荐结果。"""

    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    institution_major_id: Mapped[str] = mapped_column(
        ForeignKey("institution_majors.id"), index=True
    )
    tier: Mapped[str] = mapped_column(String(20), index=True)
    score: Mapped[float] = mapped_column(Numeric(8, 2))
    probability: Mapped[float] = mapped_column(Numeric(5, 2))
    reason: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    data_refs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    assessment: Mapped["Assessment"] = relationship(back_populates="recommendations")
    institution_major: Mapped["InstitutionMajor"] = relationship()


class TaskTemplate(TimestampMixin, Base):
    """阶段任务模板。"""

    __tablename__ = "task_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    stage: Mapped[str] = mapped_column(String(20), index=True)
    subject: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    default_minutes: Mapped[int] = mapped_column(Integer, default=60)


class StudyPlan(TimestampMixin, Base):
    """个性化学习计划。"""

    __tablename__ = "study_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160), default="考研学习计划")
    institution_major_id: Mapped[str | None] = mapped_column(
        ForeignKey("institution_majors.id"), nullable=True, index=True
    )
    target_total_score: Mapped[int] = mapped_column(Integer)
    target_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    current_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=360)
    reminder_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    plan_tasks: Mapped[list["PlanTask"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class PlanTask(TimestampMixin, Base):
    """计划中的每日任务。"""

    __tablename__ = "plan_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(160))
    task_date: Mapped[date] = mapped_column(Date, index=True)
    planned_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    is_rolled_over: Mapped[bool] = mapped_column(Boolean, default=False)
    original_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(20), default="generated")

    plan: Mapped["StudyPlan"] = relationship(back_populates="plan_tasks")


class CheckIn(TimestampMixin, Base):
    """每日学习打卡。"""

    __tablename__ = "check_ins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    subject: Mapped[str] = mapped_column(String(40), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    completion: Mapped[float] = mapped_column(Numeric(5, 2), default=100)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_makeup: Mapped[bool] = mapped_column(Boolean, default=False)


class StudyReport(TimestampMixin, Base):
    """周/月学习报告快照。"""

    __tablename__ = "study_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    period_type: Mapped[str] = mapped_column(String(20), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProcessNode(TimestampMixin, Base):
    """考研全流程关键节点。"""

    __tablename__ = "process_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    stage: Mapped[str] = mapped_column(String(20), index=True)
    typical_date: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    year: Mapped[int] = mapped_column(Integer, index=True)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    advance_days: Mapped[int] = mapped_column(Integer, default=7)
    guide: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)

    subscriptions: Mapped[list["NodeSubscription"]] = relationship(
        back_populates="node", cascade="all, delete-orphan"
    )


class NodeSubscription(TimestampMixin, Base):
    """用户对关键节点的提醒订阅。"""

    __tablename__ = "node_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    process_node_id: Mapped[str] = mapped_column(
        ForeignKey("process_nodes.id", ondelete="CASCADE"), index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    advance_days: Mapped[int] = mapped_column(Integer, default=7)
    last_reminded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    node: Mapped["ProcessNode"] = relationship(back_populates="subscriptions")


class DataCorrection(TimestampMixin, Base):
    """用户数据纠错与人工审核。"""

    __tablename__ = "data_corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    field_name: Mapped[str] = mapped_column(String(120))
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Article(TimestampMixin, Base):
    """考研资讯与政策内容。"""

    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
