# 签到（刷脸 + 管理端手动）
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Checkin, Member, Session as SessionModel, Enrollment, AdminUser
from schemas.api import FaceCheckinIn
from services.face_service import face_service
from utils.auth import get_current_member, get_current_admin
from utils.helpers import ok, to_dict


router = APIRouter(prefix="/api/checkin", tags=["checkin"])
admin_router = APIRouter(prefix="/admin/checkins", tags=["admin-checkins"])


def _resolve_day(session: SessionModel, explicit_day: Optional[int]) -> int:
    """按场次起始日期推算 day。explicit_day 优先。"""
    if explicit_day and explicit_day in (1, 2, 3):
        return explicit_day
    if session.start_date:
        today = date.today()
        delta = (today - session.start_date).days + 1
        return max(1, min(delta, 3))
    return 1


@router.post("/face")
def face_checkin(body: FaceCheckinIn, db: Session = Depends(get_db),
                 current: Member = Depends(get_current_member)):
    """扫脸签到：校验报名 + 人脸比对 + 幂等记录。"""
    sess = db.query(SessionModel).filter(SessionModel.id == body.session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="场次不存在")

    enroll = (
        db.query(Enrollment)
        .filter(Enrollment.member_id == current.id, Enrollment.session_id == sess.id)
        .first()
    )
    if not enroll:
        raise HTTPException(status_code=400, detail="未报名该场次")

    if not current.face_token:
        raise HTTPException(status_code=400, detail="请先绑定人脸")

    r = face_service.verify(current.face_token, body.face_base64)
    if not r.get("ok"):
        raise HTTPException(status_code=400, detail=r.get("msg", "人脸识别失败"))

    day = _resolve_day(sess, body.checkin_day)

    exists = (
        db.query(Checkin)
        .filter(
            Checkin.member_id == current.id,
            Checkin.session_id == sess.id,
            Checkin.checkin_day == day,
        )
        .first()
    )
    if exists:
        return ok({
            "repeat": True,
            "day": day,
            "checkin_time": exists.checkin_time.isoformat() if exists.checkin_time else None,
        })

    c = Checkin(
        member_id=current.id,
        session_id=sess.id,
        checkin_day=day,
        method="face",
    )
    db.add(c)

    # 报名状态更新为 attended
    if enroll.status == "enrolled":
        enroll.status = "attended"
    db.commit()
    db.refresh(c)

    return ok({
        "day": day,
        "score": r.get("score"),
        "checkin_time": c.checkin_time.isoformat(),
    })


# --------- 管理端 ---------
@admin_router.get("/{session_id}")
def list_checkins(session_id: int, db: Session = Depends(get_db),
                  _: AdminUser = Depends(get_current_admin)):
    rows = (
        db.query(Checkin, Member)
        .join(Member, Checkin.member_id == Member.id)
        .filter(Checkin.session_id == session_id)
        .order_by(Checkin.checkin_time.desc())
        .all()
    )
    data = []
    for c, m in rows:
        data.append({
            "id": c.id,
            "member_id": m.id,
            "member_no": m.member_no,
            "name": m.name,
            "phone": m.phone,
            "checkin_day": c.checkin_day,
            "checkin_time": c.checkin_time.isoformat() if c.checkin_time else None,
            "method": c.method,
        })
    return ok(data)


@admin_router.post("/manual")
def manual_checkin(
    member_id: int, session_id: int, checkin_day: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    m = db.query(Member).filter(Member.id == member_id).first()
    if not sess or not m:
        raise HTTPException(status_code=404, detail="场次/学员不存在")

    exists = (
        db.query(Checkin)
        .filter(
            Checkin.member_id == member_id,
            Checkin.session_id == session_id,
            Checkin.checkin_day == checkin_day,
        )
        .first()
    )
    if exists:
        return ok({"repeat": True})

    c = Checkin(
        member_id=member_id, session_id=session_id, checkin_day=checkin_day,
        method="manual", operator_id=admin.id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return ok(to_dict(c))
