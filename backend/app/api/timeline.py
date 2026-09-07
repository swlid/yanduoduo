"""考研全流程时间线与关键节点提醒接口。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import NodeSubscription, ProcessNode, TaskTemplate
from ..schemas import (
    NodeSubscriptionCreate,
    NodeSubscriptionOut,
    ProcessNodeOut,
)
from ..services.timeline import (
    next_node,
    node_payload,
    stage_for_date,
    subscription_reminders,
    upcoming_nodes,
)


router = APIRouter(tags=["时间线"])
node_router = APIRouter(prefix="/process-nodes", tags=["关键节点"])
subscription_router = APIRouter(prefix="/subscriptions", tags=["提醒订阅"])


@router.get("/timeline/current", response_model=dict)
def current_timeline(
    today: date | None = None,
    db: Session = Depends(get_db),
) -> dict:
    current = today or date.today()
    nodes = list(
        db.scalars(
            select(ProcessNode)
            .where(ProcessNode.status == "published")
            .order_by(ProcessNode.actual_date)
        ).all()
    )
    stage = stage_for_date(current)
    stage_tasks = list(
        db.scalars(
            select(TaskTemplate)
            .where(TaskTemplate.stage == stage)
            .order_by(TaskTemplate.sort_order)
        ).all()
    )
    upcoming = upcoming_nodes(nodes, current, 60)
    next_item = next_node(nodes, current)
    exam_node = next((n for n in nodes if n.key == "exam"), None)

    return {
        "today": current.isoformat(),
        "stage": stage,
        "stage_tasks": [
            {
                "id": t.id,
                "stage": t.stage,
                "subject": t.subject,
                "title": t.title,
                "default_minutes": t.default_minutes,
            }
            for t in stage_tasks
        ],
        "next_node": node_payload(next_item, current) if next_item else None,
        "upcoming_nodes": [node_payload(n, current) for n in upcoming],
        "exam_countdown": (
            (exam_node.actual_date - current).days
            if exam_node and exam_node.actual_date
            else None
        ),
    }


@node_router.get("", response_model=list[ProcessNodeOut])
def list_nodes(
    stage: str | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
) -> list[ProcessNodeOut]:
    stmt = select(ProcessNode).where(ProcessNode.status == "published")
    if stage:
        stmt = stmt.where(ProcessNode.stage == stage)
    if year:
        stmt = stmt.where(ProcessNode.year == year)
    rows = db.scalars(stmt.order_by(ProcessNode.actual_date)).all()
    return [ProcessNodeOut.model_validate(row) for row in rows]


@subscription_router.post("", response_model=NodeSubscriptionOut, status_code=201)
def create_subscription(
    payload: NodeSubscriptionCreate,
    db: Session = Depends(get_db),
) -> NodeSubscriptionOut:
    node = db.get(ProcessNode, payload.process_node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="关键节点不存在")

    existing = db.scalar(
        select(NodeSubscription).where(
            NodeSubscription.user_id == payload.user_id,
            NodeSubscription.process_node_id == payload.process_node_id,
        )
    )
    if existing is not None:
        existing.advance_days = payload.advance_days
        existing.enabled = payload.enabled
        db.commit()
        item = existing
    else:
        item = NodeSubscription(
            user_id=payload.user_id,
            process_node_id=payload.process_node_id,
            advance_days=payload.advance_days,
            enabled=payload.enabled,
        )
        db.add(item)
        db.commit()

    stmt = (
        select(NodeSubscription)
        .where(NodeSubscription.id == item.id)
        .options(selectinload(NodeSubscription.node))
    )
    refreshed = db.scalar(stmt)
    return NodeSubscriptionOut.model_validate(refreshed)


@subscription_router.get("", response_model=list[NodeSubscriptionOut])
def list_subscriptions(
    user_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[NodeSubscriptionOut]:
    stmt = select(NodeSubscription).options(selectinload(NodeSubscription.node))
    if user_id:
        stmt = stmt.where(NodeSubscription.user_id == user_id)
    rows = db.scalars(stmt.order_by(NodeSubscription.created_at.desc())).all()
    return [NodeSubscriptionOut.model_validate(row) for row in rows]


@subscription_router.delete("/{subscription_id}", response_model=dict)
def delete_subscription(
    subscription_id: str,
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(NodeSubscription, subscription_id)
    if item is None:
        raise HTTPException(status_code=404, detail="订阅不存在")
    db.delete(item)
    db.commit()
    return {"deleted": True, "id": subscription_id}


@router.get("/reminders/upcoming", response_model=list[dict])
def upcoming_reminders(
    user_id: str | None = None,
    days: int = Query(30, ge=1, le=180),
    today: date | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    current = today or date.today()
    stmt = select(NodeSubscription).options(selectinload(NodeSubscription.node))
    if user_id:
        stmt = stmt.where(NodeSubscription.user_id == user_id)
    rows = db.scalars(stmt).all()
    return subscription_reminders(list(rows), current, days)
