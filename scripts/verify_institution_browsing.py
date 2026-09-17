"""院校库浏览闭环校验：分面 → 列表筛选 → 院校详情 → 该校组合 → 对比。

前置：后端已启动（默认 http://127.0.0.1:8000），且运行 shell 不要带
HTTP(S)_PROXY（本机代理会让 httpx 走代理拿到空响应）。

用法：python scripts/verify_institution_browsing.py
"""

from __future__ import annotations

import sys

import httpx


API = "http://127.0.0.1:8000/api/v1"


def main() -> int:
    checks = 0
    with httpx.Client(timeout=20) as client:
        # 1) 分面：前端筛选项动态来源
        facets = client.get(f"{API}/institutions/facets").json()
        assert facets["total"] >= 800, facets["total"]
        assert facets["self_draw_count"] >= 30
        assert facets["has_data_count"] >= 1
        assert facets["provinces"] and facets["levels"]
        print(
            f"PASS facets：total={facets['total']} 省份={len(facets['provinces'])} "
            f"层次={[item['value'] for item in facets['levels']]} "
            f"自划线={facets['self_draw_count']} 有数据={facets['has_data_count']}"
        )
        checks += 1

        # 2) 地区筛选 + 分页
        province = facets["provinces"][0]["value"]
        page1 = client.get(
            f"{API}/institutions", params={"province": province, "page_size": 20}
        ).json()
        assert page1["total"] >= 1 and len(page1["items"]) <= 20
        assert all(item["province"] == province for item in page1["items"])
        print(f"PASS 地区筛选：{province} 共 {page1['total']} 所，首页 {len(page1['items'])} 条")
        checks += 1

        # 3) 关键词搜索（校名/代码）
        keyword = client.get(
            f"{API}/institutions", params={"keyword": "浙江", "page_size": 20}
        ).json()
        assert keyword["total"] >= 1
        print(f"PASS 关键词搜索：浙江 命中 {keyword['total']} 所")
        checks += 1

        # 4) 只看有数据 + 有数据优先排序
        with_data = client.get(
            f"{API}/institutions",
            params={"has_data": True, "sort": "has_data", "page_size": 50},
        ).json()
        assert with_data["total"] >= 1
        assert all(item["has_official_data"] for item in with_data["items"])
        print(f"PASS 只看有数据：{with_data['total']} 所均有官方数据")
        checks += 1

        no_data = client.get(
            f"{API}/institutions", params={"has_data": False, "page_size": 5}
        ).json()
        assert no_data["total"] + with_data["total"] == facets["total"]
        print(f"PASS 无数据院校可浏览：{no_data['total']} 所（合计等于总数）")
        checks += 1

        # 5) 有数据院校：详情概览 → 组合列表 → 对比
        target = next(item for item in with_data["items"] if item["name"] == "浙江大学")
        overview = client.get(f"{API}/institutions/{target['id']}/overview").json()
        assert overview["combo_count"] >= 1
        assert overview["has_official_data"] is True
        year = overview["latest_data_year"]
        combos = client.get(
            f"{API}/institution-majors",
            params={"institution_id": target["id"], "year": year, "page_size": 50},
        ).json()
        assert combos["total"] >= 1
        ids = ",".join(item["id"] for item in combos["items"][:3])
        compare = client.get(
            f"{API}/institution-majors/compare", params={"ids": ids, "year": year}
        ).json()
        assert compare["count"] == min(3, combos["total"])
        print(
            f"PASS 院校闭环：{overview['name']} 组合 {overview['combo_count']} 个、"
            f"官方覆盖 {overview['official_years']}、对比 {compare['count']} 条"
        )
        checks += 1

        # 6) 无数据院校：详情有概览、组合为空、不报错
        empty_hit = client.get(
            f"{API}/institutions", params={"keyword": "中国科学院大学", "page_size": 5}
        ).json()
        empty_target = next(
            item for item in empty_hit["items"] if item["name"] == "中国科学院大学"
        )
        empty_overview = client.get(
            f"{API}/institutions/{empty_target['id']}/overview"
        ).json()
        empty_combos = client.get(
            f"{API}/institution-majors",
            params={"institution_id": empty_target["id"], "page_size": 50},
        ).json()
        assert empty_overview["has_official_data"] is False
        assert empty_combos["total"] == empty_overview["combo_count"]
        print(
            f"PASS 空态院校：{empty_overview['name']} 无官方数据、"
            f"组合 {empty_combos['total']} 个，接口正常返回"
        )
        checks += 1

        # 7) 404 分支
        assert client.get(f"{API}/institutions/no-such-institution").status_code == 404
        assert (
            client.get(f"{API}/institutions/no-such-institution/overview").status_code
            == 404
        )
        print("PASS 404 分支：不存在院校的详情/概览均返回 404")
        checks += 1

    print(f"\n院校库浏览闭环校验完成：{checks} 项全部通过")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"FAIL 断言未通过：{exc}")
        sys.exit(1)
    except httpx.HTTPError as exc:  # pragma: no cover
        print(f"FAIL 请求失败：{exc}")
        sys.exit(1)
