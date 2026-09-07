"""端到端冒烟测试：覆盖各里程碑的核心 API。"""

from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_institution_query_and_filter(client):
    response = client.get(
        "/api/v1/institution-majors",
        params={
            "province": "上海",
            "discipline_gate": "工学",
            "min_avg_score": 340,
            "year": 2025,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert all(item["institution"]["province"] == "上海" for item in data["items"])


def test_institution_major_detail_and_compare(client):
    detail = client.get("/api/v1/institution-majors/im-001?year=2025")
    assert detail.status_code == 200
    assert len(detail.json()["admission_stats"]) == 3

    compare = client.get(
        "/api/v1/institution-majors/compare",
        params={"ids": "im-001,im-008,im-010", "year": 2025},
    )
    assert compare.status_code == 200
    assert compare.json()["count"] == 3


def test_assessment_recommendations(client):
    payload = {
        "undergrad_major": "软件工程",
        "target_provinces": ["浙江", "江苏", "上海"],
        "estimated_total_score": 350,
        "is_cross_major": False,
        "degree_type": "专硕",
    }
    response = client.post("/api/v1/assessments", json=payload)
    assert response.status_code == 201
    recommendations = response.json()["recommendations"]
    tiers = {item["tier"] for item in recommendations}
    assert tiers == {"冲刺", "稳妥", "保底"}


def test_plan_checkin_progress(client):
    plan = client.post(
        "/api/v1/plans/generate",
        json={
            "user_id": "test-user",
            "title": "测试计划",
            "target_total_score": 370,
            "target_scores": {"政治": 70, "英语": 65, "数学": 120, "专业课": 115},
            "current_scores": {"政治": 50, "英语": 55, "数学": 90, "专业课": 80},
            "start_date": "2026-09-07",
            "end_date": "2026-09-13",
            "daily_minutes": 360,
        },
    )
    assert plan.status_code == 201
    plan_id = plan.json()["id"]
    assert len(plan.json()["plan_tasks"]) == 28

    checkin = client.post(
        "/api/v1/check-ins",
        json={
            "user_id": "test-user",
            "date": "2026-09-07",
            "subject": "数学",
            "duration_minutes": 120,
            "completion": 90,
        },
    )
    assert checkin.status_code == 201

    progress = client.get(
        "/api/v1/progress",
        params={
            "user_id": "test-user",
            "start": "2026-09-07",
            "end": "2026-09-07",
        },
    )
    assert progress.status_code == 200
    assert progress.json()["total_minutes"] == 120


def test_timeline_and_subscription(client):
    timeline = client.get("/api/v1/timeline/current", params={"today": "2026-09-04"})
    assert timeline.status_code == 200
    assert timeline.json()["stage"] == "强化期"
    assert timeline.json()["next_node"]["key"] == "syllabus"

    subscription = client.post(
        "/api/v1/subscriptions",
        json={
            "user_id": "test-user",
            "process_node_id": "node-006",
            "advance_days": 14,
        },
    )
    assert subscription.status_code == 201


def test_admin_and_content(client):
    article = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "测试政策",
            "category": "政策",
            "content": "测试正文",
            "status": "published",
        },
    )
    assert article.status_code == 201

    articles = client.get("/api/v1/articles")
    assert articles.status_code == 200
    assert articles.json()[0]["title"] == "测试政策"

    correction = client.post(
        "/api/v1/corrections",
        json={
            "entity_type": "institution",
            "entity_id": "inst-001",
            "field_name": "name",
            "suggested_value": "测试值",
        },
    )
    assert correction.status_code == 201

    review = client.post(
        f"/api/v1/admin/corrections/{correction.json()['id']}/review",
        json={"status": "approved", "reviewed_by": "tester"},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "approved"
