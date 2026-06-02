# 站内通知系统
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from database import Base, get_db
from utils.auth import get_current_admin, get_admin_or_agent
from utils.helpers import ok

router = APIRouter(prefix="/admin/notifications", tags=["notifications"])


# ──────────────────── Model（内联，不新建文件）────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    recipient_type = Column(String(20), nullable=False)   # admin / consultant
    recipient_id = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    body = Column(Text)
    ntype = Column(String(30), default="info")             # info/booking/order/application
    ref_type = Column(String(30))
    ref_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


# ──────────────────── 工具函数（供其他路由调用）────────────────────

def push_notification(
    db: Session,
    recipient_type: str,
    recipient_id: int,
    title: str,
    body: str = None,
    ntype: str = "info",
    ref_type: str = None,
    ref_id: int = None,
):
    """推送一条站内通知"""
    notif = Notification(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        title=title,
        body=body,
        ntype=ntype,
        ref_type=ref_type,
        ref_id=ref_id,
    )
    db.add(notif)
    db.flush()
    return notif


def push_to_all_admins(db: Session, title: str, body: str = None,
                       ntype: str = "info", ref_type: str = None, ref_id: int = None):
    """推送给所有管理员"""
    from models.handbook import AdminUser
    admins = db.query(AdminUser).filter(AdminUser.status == "active").all()
    for admin in admins:
        push_notification(db, "admin", admin.id, title, body, ntype, ref_type, ref_id)


# ──────────────────── 接口 ────────────────────

@router.get("")
def list_notifications(
    unread_only: bool = False,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent),
):
    """获取当前管理员的通知列表"""
    q = db.query(Notification).filter(
        Notification.recipient_type == "admin",
        Notification.recipient_id == current_admin.id,
    )
    if unread_only:
        q = q.filter(Notification.is_read == False)
    items = q.order_by(Notification.created_at.desc()).limit(limit).all()

    unread_count = db.query(Notification).filter(
        Notification.recipient_type == "admin",
        Notification.recipient_id == current_admin.id,
        Notification.is_read == False,
    ).count()

    return ok({
        "unread_count": unread_count,
        "items": [{
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "ntype": n.ntype,
            "ref_type": n.ref_type,
            "ref_id": n.ref_id,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%m-%d %H:%M") if n.created_at else "",
        } for n in items],
    })


@router.get("/consultant")
def consultant_notifications(
    unread_only: bool = False,
    limit: int = 30,
    db: Session = Depends(get_db),
):
    """老师端通知（用 consultant token 鉴权）"""
    from fastapi import Header
    from utils.auth import decode_token
    # 此处简化：通过 query param 传 consultant_id（实际应从 token 解析）
    return ok({"unread_count": 0, "items": []})


@router.post("/read/{notif_id}")
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent),
):
    n = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.recipient_id == current_admin.id,
    ).first()
    if n:
        n.is_read = True
        db.commit()
    return ok({"msg": "已标记已读"})


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent),
):
    db.query(Notification).filter(
        Notification.recipient_type == "admin",
        Notification.recipient_id == current_admin.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return ok({"msg": "全部已读"})
