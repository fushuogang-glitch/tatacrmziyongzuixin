# 课程培训路由 —— 课程管理+报名+跟进+评价
# 2026-05-15 (恢复重建 2026-05-17)
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, Boolean, func
from sqlalchemy.orm import Session

from database import get_db, Base

# ══════════════════ ORM ══════════════════

class Course(Base):
    __tablename__ = "courses"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    brand = Column(String(50), default="塔塔")
    category = Column(String(50))           # 发展/增长/专案/供应商
    description = Column(Text)
    lecturer = Column(String(100))
    location = Column(String(200))
    start_date = Column(String(20))
    end_date = Column(String(20))
    max_seats = Column(Integer, default=50)
    price = Column(Numeric(10,2), default=0)
    status = Column(String(20), default="draft")  # draft/published/ongoing/ended
    review_text = Column(Text)
    video_channel_url = Column(String(500))
    highlights = Column(Text)               # JSON array of strings
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, nullable=False)
    member_id = Column(Integer)
    member_name = Column(String(100))
    member_phone = Column(String(20))
    company = Column(String(200))
    status = Column(String(20), default="pending")  # pending/contacted/notified/checked_in/completed
    checkin_method = Column(String(20))
    payment_status = Column(String(20), default="unpaid")
    contacted_at = Column(DateTime)
    notified_at = Column(DateTime)
    checked_in_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())


class CourseFollowupLog(Base):
    __tablename__ = "course_followup_logs"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    enrollment_id = Column(Integer, nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=func.now())


# ══════════════════ Schemas ══════════════════

class CourseOut(BaseModel):
    id: int
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    lecturer: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_seats: Optional[int] = 50
    price: Optional[float] = 0
    status: str = "draft"
    review_text: Optional[str] = None
    video_channel_url: Optional[str] = None
    highlights: Optional[str] = None
    enrollment_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class CourseCreate(BaseModel):
    title: str
    brand: Optional[str] = "塔塔"
    category: Optional[str] = None
    description: Optional[str] = None
    lecturer: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_seats: Optional[int] = 50
    price: Optional[float] = 0
    status: Optional[str] = "draft"

class EnrollmentOut(BaseModel):
    id: int
    course_id: int
    member_id: Optional[int] = None
    member_name: Optional[str] = None
    member_phone: Optional[str] = None
    company: Optional[str] = None
    status: str = "pending"
    checkin_method: Optional[str] = None
    payment_status: Optional[str] = "unpaid"
    course_title: Optional[str] = None
    contacted_at: Optional[datetime] = None
    notified_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ══════════════════ 小程序路由 ══════════════════
router = APIRouter(prefix="/api/v1/courses", tags=["courses"])

@router.get("")
def list_courses(
    category: Optional[str] = None,
    status: Optional[str] = None,
    brand: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Course)
    if category:
        q = q.filter(Course.category == category)
    if status:
        q = q.filter(Course.status == status)
    if brand:
        q = q.filter(Course.brand == brand)
    courses = q.order_by(Course.id.desc()).all()
    result = []
    for c in courses:
        d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        d["enrollment_count"] = db.query(CourseEnrollment).filter(CourseEnrollment.course_id == c.id).count()
        result.append(d)
    return {"code": 0, "data": result, "total": len(result)}

@router.get("/{course_id}")
def get_course(course_id: int, db: Session = Depends(get_db)):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(404, "课程不存在")
    d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
    d["enrollment_count"] = db.query(CourseEnrollment).filter(CourseEnrollment.course_id == c.id).count()
    return {"code": 0, "data": d}


# ══════════════════ 管理端路由 ══════════════════
admin_router = APIRouter(prefix="/admin/courses", tags=["courses-admin"])

@admin_router.get("")
def admin_list_courses(
    brand: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Course)
    if brand:
        q = q.filter(Course.brand == brand)
    if status:
        q = q.filter(Course.status == status)
    courses = q.order_by(Course.id.desc()).all()
    result = []
    for c in courses:
        d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
        d["enrollment_count"] = db.query(CourseEnrollment).filter(CourseEnrollment.course_id == c.id).count()
        result.append(d)
    return result

@admin_router.post("")
def admin_create_course(body: CourseCreate, db: Session = Depends(get_db)):
    c = Course(**body.dict())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@admin_router.get("/enrollments")
def admin_list_enrollments(
    course_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(CourseEnrollment)
    if course_id:
        q = q.filter(CourseEnrollment.course_id == course_id)
    if status:
        q = q.filter(CourseEnrollment.status == status)
    enrollments = q.order_by(CourseEnrollment.id.desc()).all()
    result = []
    for e in enrollments:
        d = {col.name: getattr(e, col.name) for col in e.__table__.columns}
        course = db.query(Course).filter(Course.id == e.course_id).first()
        d["course_title"] = course.title if course else None
        result.append(d)
    return result

@admin_router.get("/{course_id}")
def admin_get_course(course_id: int, db: Session = Depends(get_db)):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(404, "课程不存在")
    d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
    d["enrollment_count"] = db.query(CourseEnrollment).filter(CourseEnrollment.course_id == c.id).count()
    d["enrollments"] = []
    for e in db.query(CourseEnrollment).filter(CourseEnrollment.course_id == c.id).all():
        ed = {col.name: getattr(e, col.name) for col in e.__table__.columns}
        ed["followups"] = [
            {col.name: getattr(f, col.name) for col in f.__table__.columns}
            for f in db.query(CourseFollowupLog).filter(CourseFollowupLog.enrollment_id == e.id).order_by(CourseFollowupLog.id.desc()).all()
        ]
        d["enrollments"].append(ed)
    return d

@admin_router.put("/{course_id}")
def admin_update_course(course_id: int, body: CourseCreate, db: Session = Depends(get_db)):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(404, "课程不存在")
    for k, v in body.dict(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c

@admin_router.put("/{course_id}/publish")
def admin_publish_course(course_id: int, db: Session = Depends(get_db)):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(404, "课程不存在")
    c.status = "published"
    db.commit()
    return {"code": 0, "msg": "已发布"}

@admin_router.put("/{course_id}/end")
def admin_end_course(course_id: int, db: Session = Depends(get_db)):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(404, "课程不存在")
    c.status = "ended"
    db.commit()
    return {"code": 0, "msg": "课程已结束"}

@admin_router.put("/{course_id}/review")
def admin_review_course(course_id: int, body: dict, db: Session = Depends(get_db)):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(404, "课程不存在")
    c.review_text = body.get("review_text")
    c.video_channel_url = body.get("video_channel_url")
    c.highlights = body.get("highlights")
    db.commit()
    return {"code": 0, "msg": "回顾已发布"}

# --- 报名流程 ---
@admin_router.put("/enrollments/{enrollment_id}/contact")
def admin_contact_enrollment(enrollment_id: int, body: dict, db: Session = Depends(get_db)):
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "报名不存在")
    e.status = "contacted"
    e.contacted_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "已联系"}

@admin_router.put("/enrollments/{enrollment_id}/notify")
def admin_notify_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "报名不存在")
    e.status = "notified"
    e.notified_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "已通知"}

@admin_router.put("/enrollments/{enrollment_id}/checkin")
def admin_checkin_enrollment(enrollment_id: int, method: str = "manual", db: Session = Depends(get_db)):
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "报名不存在")
    e.status = "checked_in"
    e.checkin_method = method
    e.checked_in_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "已签到"}

@admin_router.post("/enrollments/{enrollment_id}/followup")
def admin_followup_enrollment(enrollment_id: int, body: dict, db: Session = Depends(get_db)):
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "报名不存在")
    log = CourseFollowupLog(enrollment_id=enrollment_id, content=body.get("content"))
    db.add(log)
    db.commit()
    return {"code": 0, "msg": "跟进已记录"}

@admin_router.put("/enrollments/{enrollment_id}/complete")
def admin_complete_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == enrollment_id).first()
    if not e:
        raise HTTPException(404, "报名不存在")
    e.status = "completed"
    e.completed_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "已完成"}


# ══════════════════ 小程序端报名 ══════════════════

class CourseEnrollBody(BaseModel):
    course_id: int
    member_id: Optional[int] = None
    attendee_name: Optional[str] = None
    attendee_phone: Optional[str] = None

@router.post("/enroll")
def enroll_course(body: CourseEnrollBody, db: Session = Depends(get_db)):
    """小程序端课程报名"""
    course = db.query(Course).filter(Course.id == body.course_id).first()
    if not course:
        raise HTTPException(404, "课程不存在")
    if course.status not in ("published", "ongoing"):
        raise HTTPException(400, "课程未开放报名")

    # 检查是否已报名
    existing = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == body.course_id,
        CourseEnrollment.member_phone == body.attendee_phone
    ).first()
    if existing:
        return {"code": 0, "msg": "您已报名", "data": {"id": existing.id}}

    # 检查名额
    count = db.query(CourseEnrollment).filter(CourseEnrollment.course_id == body.course_id).count()
    if course.max_seats and count >= course.max_seats:
        raise HTTPException(400, "名额已满")

    enrollment = CourseEnrollment(
        course_id=body.course_id,
        member_id=body.member_id,
        member_name=body.attendee_name or "",
        member_phone=body.attendee_phone or "",
        status="pending",
        payment_status="unpaid",
        pay_amount=course.price or 0,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return {"code": 0, "msg": "报名成功", "data": {"id": enrollment.id}}
