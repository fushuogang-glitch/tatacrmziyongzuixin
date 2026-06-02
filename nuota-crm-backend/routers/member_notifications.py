"""会员（小程序端）通知接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Member
from routers.notifications import Notification
from utils.auth import get_current_member
from utils.helpers import ok

router = APIRouter(prefix="/api/members", tags=["member-notifications"])


@router.get("/notifications")
def my_notifications(
    unread_only: bool = False,
    limit: int = 20,
    db: Session = Depends(get_db),
    current: Member = Depends(get_current_member),
):
    """小程序端：拉取会员自己的通知"""
    q = db.query(Notification).filter(
        Notification.recipient_type == "member",
        Notification.recipient_id == current.id,
    )
    if unread_only:
        q = q.filter(Notification.is_read == False)
    items = q.order_by(Notification.created_at.desc()).limit(limit).all()

    unread_count = db.query(Notification).filter(
        Notification.recipient_type == "member",
        Notification.recipient_id == current.id,
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


@router.post("/notifications/{nid}/read")
def mark_read(
    nid: int,
    db: Session = Depends(get_db),
    current: Member = Depends(get_current_member),
):
    n = db.query(Notification).filter(
        Notification.id == nid,
        Notification.recipient_type == "member",
        Notification.recipient_id == current.id,
    ).first()
    if n:
        n.is_read = True
        db.commit()
    return ok({"msg": "已读"})


@router.post("/notifications/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current: Member = Depends(get_current_member),
):
    db.query(Notification).filter(
        Notification.recipient_type == "member",
        Notification.recipient_id == current.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return ok({"msg": "全部已读"})
