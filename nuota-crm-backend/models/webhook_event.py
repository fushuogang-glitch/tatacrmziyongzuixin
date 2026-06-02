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
    # 会员事件
    "member.created":        ["sanhe"],
    "member.tier_changed":   ["sanhe"],
    "member.inactive_30d":   ["sanhe"],
    # 预约/工单事件
    "booking.created":       ["sanhe"],                                    # 新预约
    "booking.cancelled":     ["bafang"],
    "order.confirmed":       ["sanhe"],                                    # 工单确认→推给老师
    "order.completed":       ["sanhe", "qixing", "baichuan", "wulu"],      # 工单完结→多方通知
    # 收款事件
    "payment.created":       ["baichuan"],                                 # 新收款
    "payment.completed":     ["baichuan"],
    "payment.refunded":      ["baichuan"],
    # 组织/人事
    "staff.changed":         ["wulu"],                                     # 员工变更
    # 内容
    "content.published":     ["qixing"],                                   # 内容发布
    # 课程
    "course.enrolled":       ["bafang", "sanhe"],
    # 配额/安全
    "quota.exceeded":        ["bafang", "jiuyi"],
    "referral.completed":    ["sanhe"],
    "operation.suspicious":  ["siku", "jiuyi"],
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
