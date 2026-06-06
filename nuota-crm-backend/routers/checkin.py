# 签到（刷脸 + 管理端手动）
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Checkin, Member, Session as SessionModel, Enrollment, AdminUser
from schemas.api import FaceCheckinIn
from services.face_service import face_service
from utils.auth import get_current_member, get_current_admin, get_admin_or_agent
from utils.helpers import ok, to_dict


router = APIRouter(prefix="/api/checkin", tags=["checkin"])
admin_router = APIRouter(prefix="/admin/checkins", tags=["admin-checkins"])


# ─────────────────────────────────────────────────────────
# 现场扫脸签到（无需登录）：1:N 搜索 → 找出是谁 → 验证报名 → 记录签到
# 使用场景：管理员拿平板对准来场会员，自动识别 + 签到
# ─────────────────────────────────────────────────────────
class KioskCheckinIn(BaseModel):
    session_id: int
    face_base64: str          # 现场拍摄的人脸 base64
    checkin_day: Optional[int] = None




def _resolve_day(session: SessionModel, explicit_day: Optional[int]) -> int:
    """按场次起始日期推算 day。explicit_day 优先。"""
    if explicit_day and explicit_day in (1, 2, 3):
        return explicit_day
    if session.start_date:
        today = date.today()
        delta = (today - session.start_date).days + 1
        return max(1, min(delta, 3))
    return 1


@router.post("/kiosk", summary="现场扫脸签到（无需登录，1:N 搜索）")
def kiosk_checkin(body: KioskCheckinIn, db: Session = Depends(get_db)):
    """签到台模式：不需要会员登录，直接上传人脸 → 自动识别身份 → 验证报名 → 签到。"""
    # 1. 人脸搜索：在人员库中找这张脸是谁
    search_result = face_service.search(body.face_base64)
    if not search_result.get("ok"):
        raise HTTPException(status_code=400, detail=search_result.get("msg", "未识别到人脸"))

    member_id = search_result["member_id"]
    score     = search_result["score"]

    # 2. 查会员
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")

    # 3. 验证报名
    sess = db.query(SessionModel).filter(SessionModel.id == body.session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="场次不存在")

    enroll = (
        db.query(Enrollment)
        .filter(Enrollment.member_id == member_id, Enrollment.session_id == body.session_id)
        .first()
    )
    if not enroll:
        raise HTTPException(
            status_code=400,
            detail=f"【{member.name}】未报名该场次，无法签到"
        )

    # 4. 幂等记录签到
    day = _resolve_day(sess, body.checkin_day)
    exists = (
        db.query(Checkin)
        .filter(
            Checkin.member_id == member_id,
            Checkin.session_id == body.session_id,
            Checkin.checkin_day == day,
        )
        .first()
    )
    if exists:
        return ok({
            "repeat": True,
            "member_id": member_id,
            "member_name": member.name,
            "day": day,
            "score": score,
            "checkin_time": exists.checkin_time.isoformat() if exists.checkin_time else None,
            "msg": f"【{member.name}】今日已签到",
        })

    c = Checkin(
        member_id=member_id,
        session_id=body.session_id,
        checkin_day=day,
        method="face_kiosk",
    )
    db.add(c)
    if enroll.status == "enrolled":
        enroll.status = "attended"
    db.commit()
    db.refresh(c)

    return ok({
        "repeat": False,
        "member_id": member_id,
        "member_name": member.name,
        "member_no": member.member_no,
        "enterprise": member.enterprise_name,
        "score": score,
        "day": day,
        "checkin_time": c.checkin_time.isoformat(),
        "msg": f"✅ {member.name} 签到成功（第{day}天）",
    })


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

    r = face_service.verify(current.id, body.face_base64)
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
                  _: AdminUser = Depends(get_admin_or_agent)):
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
    admin: AdminUser = Depends(get_admin_or_agent),
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


@admin_router.post("/bind-face")
def admin_bind_face(
    body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    """管理端：给学员录入人脸（现场拍照录入）"""
    member_id = body.get('member_id')
    face_base64 = body.get('face_base64', '')
    if not member_id or not face_base64:
        raise HTTPException(400, '缺少 member_id 或 face_base64')

    m = db.query(Member).filter(Member.id == member_id).first()
    if not m:
        raise HTTPException(404, '学员不存在')

    result = face_service.bind(member_id, face_base64)
    if not result.get('ok'):
        raise HTTPException(400, result.get('msg', '人脸录入失败'))

    # 存 face_token 到会员表
    m.face_token = result.get('face_token', '')
    db.commit()

    return ok({
        'member_id': member_id,
        'member_name': m.name,
        'face_token': m.face_token,
        'msg': f'✅ {m.name} 人脸录入成功',
    })
