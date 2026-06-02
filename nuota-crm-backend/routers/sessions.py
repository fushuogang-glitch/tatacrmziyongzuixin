# 场次 & 报名
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Session as SessionModel, Enrollment, Member, AdminUser
from models.course_session import CourseEnrollment, CourseSession
from datetime import datetime
import random
from schemas.api import SessionCreateIn, SessionOut
from utils.auth import get_current_member, get_current_admin, get_admin_or_agent
from utils.helpers import ok, to_dict


router = APIRouter(prefix="/api/sessions", tags=["sessions"])
admin_router = APIRouter(prefix="/admin/sessions", tags=["admin-sessions"])


@router.get("/available")
def available_sessions(db: Session = Depends(get_db)):
    """可报名场次：status=open 且未满。"""
    q = (
        db.query(SessionModel)
        .filter(SessionModel.status == "open")
        .order_by(SessionModel.start_date.asc())
        .all()
    )
    return ok([to_dict(s) for s in q])


@router.post("/{sid}/enroll")
def enroll(sid: int, db: Session = Depends(get_db),
           current: Member = Depends(get_current_member)):
    s = db.query(SessionModel).filter(SessionModel.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="场次不存在")
    if s.status != "open":
        raise HTTPException(status_code=400, detail="该场次已停止报名")
    if s.enrolled >= (s.capacity or 0):
        raise HTTPException(status_code=400, detail="该场次已满")

    exists = (
        db.query(Enrollment)
        .filter(Enrollment.member_id == current.id, Enrollment.session_id == sid)
        .first()
    )
    if exists:
        return ok({"repeat": True, "id": exists.id})

    e = Enrollment(member_id=current.id, session_id=sid, status="enrolled")
    db.add(e)
    s.enrolled = (s.enrolled or 0) + 1
    if s.enrolled >= (s.capacity or 0):
        s.status = "full"

    # 同步写入 course_enrollments_v2（后台管理查这张表）
    cs = db.query(CourseSession).filter(CourseSession.id == sid).first()
    if cs:
        existing_v2 = db.query(CourseEnrollment).filter(
            CourseEnrollment.session_id == sid,
            CourseEnrollment.member_id == current.id
        ).first()
        if not existing_v2:
            enrollment_no = f"CE-{date.today().strftime('%Y%m%d')}-{random.randint(1000,9999)}"
            ce = CourseEnrollment(
                enrollment_no=enrollment_no,
                session_id=sid,
                member_id=current.id,
                consultant_id=None,
                service_id=cs.service_id,
                price_type="trial",
                paid_amount=cs.trial_price or 0,
                pay_status="pending",
                status="enrolled",
            )
            db.add(ce)
            cs.enrolled_count = (cs.enrolled_count or 0) + 1

    db.commit()
    db.refresh(e)
    return ok(to_dict(e))


# ---- 管理端 ----
@admin_router.get("")
def admin_list(db: Session = Depends(get_db), _: AdminUser = Depends(get_admin_or_agent)):
    rows = db.query(SessionModel).order_by(SessionModel.start_date.desc()).all()
    return ok([to_dict(s) for s in rows])


@admin_router.post("")
def admin_create(body: SessionCreateIn, db: Session = Depends(get_db),
                 _: AdminUser = Depends(get_admin_or_agent)):
    if db.query(SessionModel).filter(SessionModel.session_no == body.session_no).first():
        raise HTTPException(status_code=400, detail="期号已存在")
    s = SessionModel(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return ok(to_dict(s))


@admin_router.put("/{sid}")
def admin_update(sid: int, body: SessionCreateIn, db: Session = Depends(get_db),
                 _: AdminUser = Depends(get_admin_or_agent)):
    s = db.query(SessionModel).filter(SessionModel.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="场次不存在")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return ok(to_dict(s))


@admin_router.put("/{sid}/status")
def admin_status(sid: int, status_value: str, db: Session = Depends(get_db),
                 _: AdminUser = Depends(get_admin_or_agent)):
    s = db.query(SessionModel).filter(SessionModel.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="场次不存在")
    if status_value not in ("open", "full", "closed", "finished"):
        raise HTTPException(status_code=400, detail="非法 status")
    s.status = status_value
    db.commit()
    return ok(to_dict(s))
