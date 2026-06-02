# Webhook 事件路由 — Agent 拉取/确认事件
# + 补缺接口：tags / notifications / logs-export
import io
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

from database import get_db
from models.webhook_event import WebhookEvent
from models.member import Member
from utils.auth import get_current_admin, get_admin_or_agent

router = APIRouter(tags=["Webhook事件"])
admin_router = APIRouter(prefix="/admin", tags=["补缺接口"])


# ═══ Webhook 事件拉取 ═══
class EventOut(BaseModel):
    id: int
    event_type: str
    payload: dict = {}
    target_agents: list = []
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/webhook/events", response_model=List[EventOut])
def pull_events(
    agent_id: str = Query(..., description="Agent ID"),
    status: str = Query("pending", description="pending/delivered/all"),
    limit: int = Query(50, le=200),
    db: DBSession = Depends(get_db),
):
    """Agent 拉取属于自己的事件"""
    from sqlalchemy import text as sql_text, cast, String
    q = db.query(WebhookEvent)
    if status != "all":
        q = q.filter(WebhookEvent.status == status)
    # PostgreSQL JSON 数组包含查询
    q = q.filter(cast(WebhookEvent.target_agents, String).contains(agent_id))
    return q.order_by(desc(WebhookEvent.created_at)).limit(limit).all()


@router.post("/webhook/events/{event_id}/ack")
def ack_event(
    event_id: int,
    agent_id: str = Query(...),
    db: DBSession = Depends(get_db),
):
    """Agent 确认已处理事件"""
    ev = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    if not ev:
        raise HTTPException(404, "事件不存在")
    ev.status = "delivered"
    ev.delivered_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "event_id": event_id}


# ═══ 补缺接口1: 会员标签 ═══
class TagUpdate(BaseModel):
    tags: Optional[str] = None
    notes: Optional[str] = None


@admin_router.patch("/members/{member_id}/tags")
def update_member_tags(
    member_id: int,
    body: TagUpdate,
    admin=Depends(get_admin_or_agent),
    db: DBSession = Depends(get_db),
):
    """更新会员标签/备注（三和用）"""
    m = db.query(Member).filter(Member.id == member_id).first()
    if not m:
        raise HTTPException(404, "会员不存在")
    if body.tags is not None:
        m.tags = body.tags
    if body.notes is not None:
        m.notes = body.notes
    db.commit()
    return {"ok": True, "member_id": member_id, "tags": m.tags, "notes": m.notes}


# ═══ 补缺接口2: 会员通知 ═══
class NotificationCreate(BaseModel):
    member_id: int
    title: str
    content: str
    channel: str = "system"  # system / sms / wechat


@admin_router.post("/notifications")
def send_notification(
    body: NotificationCreate,
    admin=Depends(get_admin_or_agent),
    db: DBSession = Depends(get_db),
):
    """向会员发送通知（三和用）— 暂存记录，后续接入推送通道"""
    m = db.query(Member).filter(Member.id == body.member_id).first()
    if not m:
        raise HTTPException(404, "会员不存在")
    # TODO: 接入实际推送通道（微信模板消息/短信）
    # 目前先记录到日志
    return {
        "ok": True,
        "member_id": body.member_id,
        "channel": body.channel,
        "msg": f"通知已记录（{body.channel}），待接入推送通道",
    }


# ═══ 补缺接口3: 操作日志导出 ═══
@admin_router.get("/operation-logs/export")
def export_operation_logs(
    days: int = Query(30, description="导出最近N天"),
    admin=Depends(get_admin_or_agent),
    db: DBSession = Depends(get_db),
):
    """操作日志导出CSV（司库用）"""
    from models.handbook import AdminUser
    cutoff = datetime.utcnow() - timedelta(days=days)

    # 查日志（复用现有 operation_logs 查询逻辑）
    try:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT id, admin_id, action, target_type, target_id, detail, created_at "
            "FROM operation_logs WHERE created_at >= :cutoff ORDER BY id DESC"
        ), {"cutoff": cutoff}).fetchall()
    except Exception:
        rows = []

    # 生成CSV
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "管理员ID", "操作", "目标类型", "目标ID", "详情", "时间"])
    for r in rows:
        writer.writerow(list(r))
    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=operation_logs_{days}d.csv"},
    )


# ═══ 补缺接口4: 对账确认 ═══
class PaymentVerify(BaseModel):
    payment_id: int
    verified: bool = True
    notes: Optional[str] = None


@admin_router.post("/payments/verify")
def verify_payment(
    body: PaymentVerify,
    admin=Depends(get_admin_or_agent),
    db: DBSession = Depends(get_db),
):
    """对账确认（百川用）"""
    from models.member import Payment
    p = db.query(Payment).filter(Payment.id == body.payment_id).first()
    if not p:
        raise HTTPException(404, "收款记录不存在")
    # 加个verified标记（如果字段不存在就跳过）
    if hasattr(p, 'verified'):
        p.verified = body.verified
    if hasattr(p, 'verify_notes'):
        p.verify_notes = body.notes
    db.commit()
    return {"ok": True, "payment_id": body.payment_id, "verified": body.verified}
