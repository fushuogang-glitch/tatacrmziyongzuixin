# Webhook 事件总线 — CRM 主动推送事件给 Agent
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Session as DBSession

from database import Base

logger = logging.getLogger("webhook_events")


class WebhookEvent(Base):
    """Webhook 事件记录表"""
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)   # member.created / payment.completed ...
    payload = Column(JSON, nullable=True)                          # 事件数据
    target_agents = Column(JSON, nullable=True)                    # ["sanhe", "bafang"]
    status = Column(String(20), default="pending")                 # pending / delivered / failed
    created_at = Column(DateTime, server_default=func.now())
    delivered_at = Column(DateTime, nullable=True)
    error_msg = Column(Text, nullable=True)


# ═══ 事件定义 ═══
EVENT_ROUTING = {
    "member.created":        ["sanhe"],
    "member.tier_changed":   ["sanhe"],
    "booking.created":       ["bafang"],
    "booking.cancelled":     ["bafang"],
    "payment.completed":     ["baichuan"],
    "payment.refunded":      ["baichuan"],
    "quota.exceeded":        ["bafang", "jiuyi"],
    "referral.completed":    ["sanhe"],
    "member.inactive_30d":   ["sanhe"],
    "operation.suspicious":  ["siku", "jiuyi"],
    "course.enrolled":       ["bafang", "sanhe"],
    "order.completed":       ["sanhe", "baichuan"],
}


def emit_event(
    db: DBSession,
    event_type: str,
    payload: Dict[str, Any],
    target_agents: Optional[List[str]] = None,
):
    """
    发射事件：写入事件表，Agent通过轮询或推送获取。
    target_agents 默认从 EVENT_ROUTING 取。
    """
    if target_agents is None:
        target_agents = EVENT_ROUTING.get(event_type, [])

    event = WebhookEvent(
        event_type=event_type,
        payload=payload,
        target_agents=target_agents,
        status="pending",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(f"[EVENT] {event_type} → {target_agents} | id={event.id}")
    return event
