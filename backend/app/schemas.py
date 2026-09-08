"""API 输入输出模型。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class InstitutionOut(ORMModel):
    id: str
    code: str
    name: str
    short_name: str
    province: str
    city: str
    level: str
    category: str
    is_self_draw: bool
    official_url: str | None = None
    logo_url: str | None = None
    tags: list[Any] = []
    status: str


class MajorOut(ORMModel):
    id: str
    code: str
    name: str
    discipline_gate: str
    discipline_level1: str
    degree_type: str
    is_cross_allowed: bool
    cross_condition: str | None = None
    apply_condition: str | None = None
    research_directions: list[Any] = []
    status: str


class AdmissionStatOut(ORMModel):
    id: str
    year: int
    plan_total: int | None = None
    plan_unified: int | None = None
    recommended_count: int | None = None
    recommended_ratio: float | None = None
    applicant_count: int | None = None
    admitted_count: int | None = None
    report_rate: float | None = None
    reexam_count: int | None = None
    reexam_admit_rate: float | None = None
    max_score: float | None = None
    min_score: float | None = None
    avg_score: float | None = None
    national_line: float | None = None
    self_line: float | None = None
    college_line: float | None = None
    transfer_quota: int | None = None
    metrics: dict[str, Any] = {}
    source_url: str | None = None
    source_name: str
    source_year: int
    collected_at: datetime
    data_quality: str
    review_status: str


class InstitutionMajorSummaryOut(ORMModel):
    id: str
    faculty_name: str
    study_mode: str
    length: float | None = None
    tuition: str | None = None
    scholarship: str | None = None
    exam_basic: dict[str, Any] = {}
    exam_major: dict[str, Any] = {}
    reexam_form: dict[str, Any] = {}
    additional_exam: str | None = None
    institution: InstitutionOut
    major: MajorOut
    latest_stat: AdmissionStatOut | None = None


class InstitutionMajorDetailOut(InstitutionMajorSummaryOut):
    admission_stats: list[AdmissionStatOut] = []


class PageOut(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class AssessmentCreate(BaseModel):
    undergrad_major: str
    target_provinces: list[str] = []
    estimated_total_score: int
    is_cross_major: bool = False
    degree_type: Literal["学硕", "专硕", "不限"] = "不限"
    target_level: Literal["985", "211", "双一流", "普通"] | None = None


class AssessmentOut(ORMModel):
    id: str
    undergrad_major: str
    target_provinces: list[Any] = []
    estimated_total_score: int
    is_cross_major: bool
    degree_type: str
    target_level: str | None = None
    profile: dict[str, Any] = {}


class RecommendationOut(ORMModel):
    id: str
    assessment_id: str
    institution_major_id: str
    tier: str
    score: float
    probability: float
    reason: dict[str, Any] = {}
    data_refs: dict[str, Any] = {}
    institution_major: InstitutionMajorSummaryOut


class AssessmentDetailOut(AssessmentOut):
    recommendations: list[RecommendationOut] = []


class PlanGenerateRequest(BaseModel):
    user_id: str | None = None
    title: str | None = None
    institution_major_id: str | None = None
    target_total_score: int
    target_scores: dict[str, float]
    current_scores: dict[str, float] = {}
    start_date: date
    end_date: date
    daily_minutes: int = 360
    reminder_time: str | None = None


class PlanTaskOut(ORMModel):
    id: str
    plan_id: str
    subject: str
    title: str
    task_date: date
    planned_minutes: int
    status: str
    is_rolled_over: bool
    original_date: date | None = None
    completed_at: datetime | None = None
    sort_order: int
    source: str


class StudyPlanOut(ORMModel):
    id: str
    user_id: str | None = None
    title: str
    institution_major_id: str | None = None
    target_total_score: int
    target_scores: dict[str, Any] = {}
    current_scores: dict[str, Any] = {}
    start_date: date
    end_date: date
    daily_minutes: int
    reminder_time: str | None = None
    status: str


class StudyPlanDetailOut(StudyPlanOut):
    plan_tasks: list[PlanTaskOut] = []
    rollover_count: int = 0


class CheckInCreate(BaseModel):
    user_id: str | None = None
    date: date
    subject: str
    duration_minutes: int
    completion: float = 100
    note: str | None = None
    is_makeup: bool = False


class CheckInOut(ORMModel):
    id: str
    user_id: str | None = None
    date: date
    subject: str
    duration_minutes: int
    completion: float
    note: str | None = None
    is_makeup: bool


class ProcessNodeOut(ORMModel):
    id: str
    key: str
    name: str
    stage: str
    typical_date: dict[str, Any] = {}
    year: int
    actual_date: date | None = None
    advance_days: int
    guide: str | None = None
    source_url: str | None = None
    status: str


class NodeSubscriptionCreate(BaseModel):
    user_id: str | None = None
    process_node_id: str
    advance_days: int = 7
    enabled: bool = True


class NodeSubscriptionOut(ORMModel):
    id: str
    user_id: str | None = None
    process_node_id: str
    enabled: bool
    advance_days: int
    last_reminded_at: datetime | None = None
    node: ProcessNodeOut


class InstitutionCreate(BaseModel):
    code: str
    name: str
    short_name: str = ""
    province: str
    city: str
    level: str
    category: str
    is_self_draw: bool = False
    official_url: str | None = None
    logo_url: str | None = None
    tags: list[Any] = []


class InstitutionUpdate(BaseModel):
    short_name: str | None = None
    province: str | None = None
    city: str | None = None
    level: str | None = None
    category: str | None = None
    is_self_draw: bool | None = None
    official_url: str | None = None
    logo_url: str | None = None
    tags: list[Any] | None = None


class MajorCreate(BaseModel):
    code: str
    name: str
    discipline_gate: str
    discipline_level1: str
    degree_type: str
    is_cross_allowed: bool = True
    cross_condition: str | None = None
    apply_condition: str | None = None
    research_directions: list[Any] = []


class MajorUpdate(BaseModel):
    name: str | None = None
    discipline_gate: str | None = None
    discipline_level1: str | None = None
    degree_type: str | None = None
    is_cross_allowed: bool | None = None
    cross_condition: str | None = None
    apply_condition: str | None = None
    research_directions: list[Any] | None = None


class InstitutionMajorCreate(BaseModel):
    institution_id: str
    major_id: str
    faculty_name: str = ""
    study_mode: str = "全日制"
    length: float | None = None
    tuition: str | None = None
    scholarship: str | None = None
    exam_basic: dict[str, Any] = {}
    exam_major: dict[str, Any] = {}
    reexam_form: dict[str, Any] = {}
    additional_exam: str | None = None


class InstitutionMajorUpdate(BaseModel):
    faculty_name: str | None = None
    study_mode: str | None = None
    length: float | None = None
    tuition: str | None = None
    scholarship: str | None = None
    exam_basic: dict[str, Any] | None = None
    exam_major: dict[str, Any] | None = None
    reexam_form: dict[str, Any] | None = None
    additional_exam: str | None = None


class AdmissionStatCreate(BaseModel):
    institution_major_id: str
    year: int
    plan_total: int | None = None
    plan_unified: int | None = None
    recommended_count: int | None = None
    recommended_ratio: float | None = None
    applicant_count: int | None = None
    admitted_count: int | None = None
    report_rate: float | None = None
    reexam_count: int | None = None
    reexam_admit_rate: float | None = None
    max_score: float | None = None
    min_score: float | None = None
    avg_score: float | None = None
    national_line: float | None = None
    self_line: float | None = None
    college_line: float | None = None
    transfer_quota: int | None = None
    metrics: dict[str, Any] = {}
    source_url: str | None = None
    source_name: str = "人工录入"
    source_year: int
    data_quality: str = "official"
    review_status: str = "pending"


class AdmissionStatUpdate(BaseModel):
    plan_total: int | None = None
    plan_unified: int | None = None
    recommended_count: int | None = None
    recommended_ratio: float | None = None
    applicant_count: int | None = None
    admitted_count: int | None = None
    report_rate: float | None = None
    reexam_count: int | None = None
    reexam_admit_rate: float | None = None
    max_score: float | None = None
    min_score: float | None = None
    avg_score: float | None = None
    national_line: float | None = None
    self_line: float | None = None
    college_line: float | None = None
    transfer_quota: int | None = None
    metrics: dict[str, Any] | None = None
    source_url: str | None = None
    source_name: str | None = None
    source_year: int | None = None
    data_quality: str | None = None
    review_status: str | None = None


class AdmissionStatReview(BaseModel):
    review_status: Literal["approved", "rejected", "pending"]
    reviewed_by: str | None = None


class CorrectionCreate(BaseModel):
    user_id: str | None = None
    entity_type: str
    entity_id: str
    field_name: str
    original_value: str | None = None
    suggested_value: str | None = None
    note: str | None = None


class CorrectionOut(ORMModel):
    id: str
    user_id: str | None = None
    entity_type: str
    entity_id: str
    field_name: str
    original_value: str | None = None
    suggested_value: str | None = None
    note: str | None = None
    status: str


class CorrectionReview(BaseModel):
    status: Literal["approved", "rejected"]
    reviewed_by: str | None = None


class ArticleCreate(BaseModel):
    title: str
    category: str
    summary: str | None = None
    content: str
    source_name: str | None = None
    source_url: str | None = None
    status: Literal["draft", "published"] = "draft"


class ArticleUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    summary: str | None = None
    content: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    status: Literal["draft", "published"] | None = None


class ArticleOut(ORMModel):
    id: str
    title: str
    category: str
    summary: str | None = None
    content: str
    source_name: str | None = None
    source_url: str | None = None
    status: str
    published_at: datetime | None = None
