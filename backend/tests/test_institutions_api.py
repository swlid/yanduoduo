"""院校库浏览闭环：院校列表增强、分面与详情概览接口测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import AdmissionStat

LEVEL_ORDER = ["985", "211", "双一流", "普通"]


def _official_import_csv() -> bytes:
    header = (
        "institution_code,major_code,year,self_line,college_line,national_line,"
        "metrics,source_url,source_name,source_year,data_quality,review_status\n"
    )
    row = (
        "10335,081200,2025,300,,,{},https://example.com/test-official,"
        "__test_official__,2025,official,pending\n"
    )
    return (header + row).encode("utf-8")


def _cleanup_test_official_stat() -> None:
    session = SessionLocal()
    try:
        rows = (
            session.query(AdmissionStat)
            .filter(AdmissionStat.source_name == "__test_official__")
            .all()
        )
        for row in rows:
            session.delete(row)
        session.commit()
    finally:
        session.close()


def test_institutions_list_new_fields(client: TestClient):
    response = client.get("/api/v1/institutions", params={"page": 1, "page_size": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 20
    assert len(data["items"]) == 5
    item = data["items"][0]
    for field in ("id", "code", "name", "province", "level", "category", "is_self_draw"):
        assert field in item
    for field in (
        "combo_count",
        "official_combo_count",
        "official_years",
        "has_official_data",
        "latest_data_year",
    ):
        assert field in item
    assert isinstance(item["combo_count"], int)
    assert isinstance(item["official_combo_count"], int)
    assert isinstance(item["official_years"], list)
    assert isinstance(item["has_official_data"], bool)
    assert item["latest_data_year"] is None or isinstance(item["latest_data_year"], int)


def test_institutions_default_and_name_sort(client: TestClient):
    default_items = client.get(
        "/api/v1/institutions", params={"page_size": 10}
    ).json()["items"]
    ranks = [
        LEVEL_ORDER.index(item["level"])
        for item in default_items
        if item["level"] in LEVEL_ORDER
    ]
    assert ranks == sorted(ranks), "默认排序应按 985→211→双一流→普通 降序"

    name_items = client.get(
        "/api/v1/institutions", params={"sort": "name", "page_size": 10}
    ).json()["items"]
    names = [item["name"] for item in name_items]
    assert names == sorted(names), "sort=name 应按名称升序"


def test_institution_facets(client: TestClient):
    response = client.get("/api/v1/institutions/facets")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 20
    assert data["self_draw_count"] >= 1
    assert data["has_data_count"] >= 0
    assert data["provinces"], "省份分面不应为空"
    for row in data["provinces"]:
        assert row["value"] not in ("", "暂无", "未知")
        assert row["count"] >= 1
    counts = [row["count"] for row in data["provinces"]]
    assert counts == sorted(counts, reverse=True), "省份分面应按数量降序"
    level_values = [row["value"] for row in data["levels"]]
    assert level_values == [lv for lv in LEVEL_ORDER if lv in level_values]
    for row in data["categories"]:
        assert row["value"] not in ("", "暂无", "未知")


def test_institution_overview_and_404(client: TestClient):
    found = client.get(
        "/api/v1/institutions", params={"keyword": "浙江大学", "page_size": 1}
    ).json()["items"]
    assert found, "种子库中应能检索到浙江大学"
    institution_id = found[0]["id"]

    response = client.get(f"/api/v1/institutions/{institution_id}/overview")
    assert response.status_code == 200
    data = response.json()
    for field in (
        "name",
        "code",
        "province",
        "level",
        "is_self_draw",
        "combo_count",
        "official_combo_count",
        "official_years",
        "has_official_data",
        "latest_data_year",
        "latest_updated_at",
    ):
        assert field in data
    assert data["combo_count"] >= 1

    assert client.get("/api/v1/institutions/no-such-id/overview").status_code == 404
    assert client.get("/api/v1/institutions/no-such-id").status_code == 404


def test_has_data_filter_and_official_metrics(client: TestClient):
    """导入一条官方数据并审核后，has_data 过滤与官方覆盖字段应立即生效。"""
    before = client.get("/api/v1/institutions", params={"has_data": True}).json()
    assert before["total"] == 0, "种子库仅有 mock 数据，不应有官方数据院校"

    response = client.post(
        "/api/v1/admin/import",
        data={"entity_type": "admission_stat"},
        files={"file": ("official.csv", _official_import_csv(), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["errors"] == []

    pending = client.get(
        "/api/v1/admin/admission-stats",
        params={"review_status": "pending", "page_size": 100},
    ).json()
    target = [
        row for row in pending["items"] if row["source_name"] == "__test_official__"
    ]
    assert target, "应能查到刚导入的待审核官方数据"
    review = client.post(
        f"/api/v1/admin/admission-stats/{target[0]['id']}/review",
        json={"review_status": "approved", "reviewed_by": "pytest"},
    )
    assert review.status_code == 200

    try:
        with_data = client.get(
            "/api/v1/institutions",
            params={"has_data": True, "sort": "has_data", "page_size": 10},
        ).json()
        assert with_data["total"] >= 1
        first = with_data["items"][0]
        assert first["has_official_data"] is True
        assert first["official_combo_count"] >= 1
        assert first["official_years"] == [2025]
        assert first["latest_data_year"] == 2025
        assert first["combo_count"] >= 1

        without_data = client.get(
            "/api/v1/institutions", params={"has_data": False, "page_size": 1}
        ).json()
        assert without_data["total"] == 20 - with_data["total"]

        facets = client.get("/api/v1/institutions/facets").json()
        assert facets["has_data_count"] >= 1

        overview = client.get(f"/api/v1/institutions/{first['id']}/overview").json()
        assert overview["official_years"] == [2025]
        assert overview["latest_updated_at"] is not None
    finally:
        _cleanup_test_official_stat()
