"""全流程验收冒烟脚本。运行前需启动后端。"""

from __future__ import annotations

import sys

import httpx


BASE_URL = "http://127.0.0.1:8000"
API = f"{BASE_URL}/api/v1"


def main() -> int:
    with httpx.Client(timeout=20) as client:
        try:
            assert client.get(f"{BASE_URL}/health").json()["status"] == "ok"
            print("PASS health")

            institutions = client.get(f"{API}/institutions", params={"page_size": 20}).json()
            assert institutions["total"] > 0
            print("PASS institutions query")

            filtered = client.get(
                f"{API}/institution-majors",
                params={
                    "province": "上海",
                    "discipline_gate": "工学",
                    "min_avg_score": 340,
                    "year": 2025,
                },
            ).json()
            assert filtered["total"] > 0
            print("PASS institution-majors filter")

            detail = client.get(f"{API}/institution-majors/im-001", params={"year": 2025}).json()
            assert len(detail["admission_stats"]) >= 1
            print("PASS institution-major detail")

            compare = client.get(
                f"{API}/institution-majors/compare",
                params={"ids": "im-001,im-008,im-010", "year": 2025},
            ).json()
            assert compare["count"] == 3
            print("PASS institution-major compare")

            assessment = client.post(
                f"{API}/assessments",
                json={
                    "undergrad_major": "软件工程",
                    "target_provinces": ["浙江", "江苏", "上海"],
                    "estimated_total_score": 350,
                    "is_cross_major": False,
                    "degree_type": "专硕",
                },
            ).json()
            assert assessment["recommendations"]
            print("PASS assessment recommendations")

            plan = client.post(
                f"{API}/plans/generate",
                json={
                    "user_id": "acceptance-user",
                    "title": "验收计划",
                    "target_total_score": 370,
                    "target_scores": {"政治": 70, "英语": 65, "数学": 120, "专业课": 115},
                    "current_scores": {"政治": 50, "英语": 55, "数学": 90, "专业课": 80},
                    "start_date": "2026-09-07",
                    "end_date": "2026-09-13",
                    "daily_minutes": 360,
                },
            ).json()
            assert plan["plan_tasks"]
            print("PASS plan generate")

            client.post(
                f"{API}/check-ins",
                json={
                    "user_id": "acceptance-user",
                    "date": "2026-09-07",
                    "subject": "数学",
                    "duration_minutes": 120,
                    "completion": 90,
                },
            ).raise_for_status()
            print("PASS check-in")

            progress = client.get(
                f"{API}/progress",
                params={
                    "user_id": "acceptance-user",
                    "start": "2026-09-07",
                    "end": "2026-09-07",
                },
            ).json()
            assert progress["total_minutes"] >= 1
            print("PASS progress")

            timeline = client.get(
                f"{API}/timeline/current", params={"today": "2026-09-04"}
            ).json()
            assert timeline["next_node"]
            print("PASS timeline current")

            client.post(
                f"{API}/subscriptions",
                json={
                    "user_id": "acceptance-user",
                    "process_node_id": "node-006",
                    "advance_days": 14,
                },
            ).raise_for_status()
            print("PASS subscription")

            client.post(
                f"{API}/admin/articles",
                json={
                    "title": "验收文章",
                    "category": "政策",
                    "content": "验收正文",
                    "status": "published",
                },
            ).raise_for_status()
            print("PASS admin article")

            correction = client.post(
                f"{API}/corrections",
                json={
                    "user_id": "acceptance-user",
                    "entity_type": "institution",
                    "entity_id": "inst-001",
                    "field_name": "name",
                    "suggested_value": "验收值",
                },
            ).json()
            client.post(
                f"{API}/admin/corrections/{correction['id']}/review",
                json={"status": "approved", "reviewed_by": "acceptance"},
            ).raise_for_status()
            print("PASS correction review")

            print("\nALL ACCEPTANCE CHECKS PASSED")
            return 0
        except AssertionError as exc:
            print(f"FAIL assertion: {exc}")
            return 1
        except httpx.HTTPError as exc:
            print(f"FAIL http: {exc}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
