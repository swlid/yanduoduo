"""考研全流程时间线计算。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..models import NodeSubscription, ProcessNode


def stage_for_date(today: date) -> str:
    month = today.month
    if 3 <= month <= 6:
        return "基础期"
    if 7 <= month <= 9:
        return "强化期"
    if 10 <= month <= 12:
        return "冲刺期"
    if 1 <= month <= 4:
        return "复试期"
    return "录取期"


def _dated(nodes: list[ProcessNode]) -> list[ProcessNode]:
    return [n for n in nodes if n.actual_date is not None]


def next_node(nodes: list[ProcessNode], today: date) -> ProcessNode | None:
    upcoming = sorted(
        [n for n in _dated(nodes) if n.actual_date >= today],
        key=lambda n: n.actual_date,
    )
    return upcoming[0] if upcoming else None


def upcoming_nodes(
    nodes: list[ProcessNode], today: date, days: int
) -> list[ProcessNode]:
    end = today + timedelta(days=days)
    return sorted(
        [
            n
            for n in _dated(nodes)
            if today <= n.actual_date <= end
        ],
        key=lambda n: n.actual_date,
    )


def countdown(target: date, today: date) -> int:
    return (target - today).days


def node_payload(node: ProcessNode, today: date) -> dict[str, Any]:
    return {
        "id": node.id,
        "key": node.key,
        "name": node.name,
        "stage": node.stage,
        "year": node.year,
        "actual_date": node.actual_date.isoformat() if node.actual_date else None,
        "advance_days": node.advance_days,
        "guide": node.guide,
        "status": node.status,
        "days_left": countdown(node.actual_date, today)
        if node.actual_date
        else None,
    }


def subscription_reminders(
    subscriptions: list[NodeSubscription],
    today: date,
    days: int,
) -> list[dict[str, Any]]:
    end = today + timedelta(days=days)
    result: list[dict[str, Any]] = []
    for sub in subscriptions:
        if not sub.enabled or sub.node.actual_date is None:
            continue
        remind_date = sub.node.actual_date - timedelta(days=sub.advance_days)
        if today <= remind_date <= end:
            result.append(
                {
                    "subscription_id": sub.id,
                    "node_id": sub.node.id,
                    "node_name": sub.node.name,
                    "node_date": sub.node.actual_date.isoformat(),
                    "remind_date": remind_date.isoformat(),
                    "advance_days": sub.advance_days,
                    "guide": sub.node.guide,
                }
            )
    return sorted(result, key=lambda x: x["remind_date"])
