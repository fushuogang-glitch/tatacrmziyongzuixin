# 课程场次统一管理 API
# CRM管理端 + 小程序端 + 三和跟进webhook
from datetime import date, datetime, timedelta
from typing import Optional
import random

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Member, Consultant, Service, AdminUser,
)
from models.course_session import (
    CourseSession, CourseEnrollment, CourseCheckin, CourseFollowup,
)
from utils.auth import get_current_admin, get_current_member
from utils.helpers import ok, to_dict

# ============================================================
# 路由
# ============================================================
admin_router = APIRouter(prefix="/admin/course-sessions", tags=["课程场次-管理端"])
router = APIRouter(prefix="/api/v1/course-sessions", tags=["课程场次-小程序端"])
webhook_router = APIRouter(prefix="/webhook/course", tags=["课程场次-webhook"])


# ============================================================
# Schemas
# ============================================================
class SessionCreate(BaseModel):
    service_id: int
    title: str
    edition: Optional[int] = 1
    city: Optional[str] = None
    venue: Optional[str] = None
    start_date: str                    # YYYY-MM-DD
    end_date: str
    duration_days: Optional[int] = 3
    capacity: Optional[int] = 50
    normal_price: Optional[float] = None
    trial_price: Optional[float] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    highlights: Optional[str] = None


class EnrollCreate(BaseModel):
    session_id: int
    price_type: Optional[str] = "normal"   # normal/trial


# ============================================================
# 管理端 — 场次CRUD
# ============================================================

@admin_router.get("")
def admin_list_sessions(
    status: Optional[str] = None,
    service_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """场次列表（可按状态/课程筛选）"""
    q = db.query(CourseSession)
    if status:
        q = q.filter(CourseSession.status == status)
    if service_id:
        q = q.filter(CourseSession.service_id == service_id)
    sessions = q.order_by(desc(CourseSession.id)).all()

    result = []
    for s in sessions:
        d = to_dict(s)
        svc = db.query(Service).filter(Service.id == s.service_id).first()
        d['service_name'] = svc.name if svc else ''
        d['service_category'] = svc.category if svc else ''
        result.append(d)
    return ok(result)


@admin_router.post("")
def admin_create_session(
    body: SessionCreate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """创建课程场次"""
    svc = db.query(Service).filter(Service.id == body.service_id).first()
    if not svc:
        raise HTTPException(404, "课程产品不存在")

    session_no = f"CS-{date.today().strftime('%Y%m%d')}-{random.randint(1000,9999)}"
    cs = CourseSession(
        session_no=session_no,
        service_id=body.service_id,
        title=body.title or f"第{body.edition}期·{svc.name}",
        edition=body.edition,
        city=body.city,
        venue=body.venue,
        start_date=date.fromisoformat(body.start_date),
        end_date=date.fromisoformat(body.end_date),
        duration_days=body.duration_days,
        capacity=body.capacity,
        normal_price=body.normal_price or svc.price,
        trial_price=body.trial_price or svc.trial_price,
        description=body.description or svc.description,
        cover_image=body.cover_image or svc.cover_image,
        highlights=body.highlights,
        status="enrolling",
    )
    db.add(cs)
    db.commit()
    db.refresh(cs)
    return ok(to_dict(cs))


@admin_router.put("/{sid}")
def admin_update_session(
    sid: int, body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """更新场次信息"""
    cs = db.query(CourseSession).filter(CourseSession.id == sid).first()
    if not cs:
        raise HTTPException(404, "场次不存在")
    allowed = [
        "title", "edition", "city", "venue", "start_date", "end_date",
        "duration_days", "capacity", "normal_price", "trial_price",
        "description", "cover_image", "highlights", "status",
    ]
    for k, v in body.items():
        if k in allowed:
            if k in ("start_date", "end_date") and isinstance(v, str):
                v = date.fromisoformat(v)
            setattr(cs, k, v)
    db.commit()
    return ok(to_dict(cs))


@admin_router.delete("/{sid}")
def admin_delete_session(
    sid: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    cs = db.query(CourseSession).filter(CourseSession.id == sid).first()
    if not cs:
        raise HTTPException(404, "场次不存在")
    if cs.enrolled_count > 0:
        raise HTTPException(400, f"已有{cs.enrolled_count}人报名，不可删除")
    db.delete(cs)
    db.commit()
    return ok({"deleted": sid})


# ============================================================
# 管理端 — 报名管理
# ============================================================

@admin_router.get("/{sid}/enrollments")
def admin_list_enrollments(
    sid: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """查看场次下所有报名（含会员信息+签到记录）"""
    enrollments = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.session_id == sid)
        .order_by(CourseEnrollment.id)
        .all()
    )
    member_ids = list({e.member_id for e in enrollments})
    members_map = {
        m.id: m for m in db.query(Member).filter(Member.id.in_(member_ids)).all()
    } if member_ids else {}
    consultant_ids = list({e.consultant_id for e in enrollments if e.consultant_id})
    consultants_map = {
        c.id: c for c in db.query(Consultant).filter(Consultant.id.in_(consultant_ids)).all()
    } if consultant_ids else {}

    result = []
    for e in enrollments:
        d = to_dict(e)
        m = members_map.get(e.member_id)
        c = consultants_map.get(e.consultant_id) if e.consultant_id else None
        d['member_name'] = m.name if m else ''
        d['enterprise_name'] = getattr(m, 'enterprise_name', '') if m else ''
        d['member_phone'] = m.phone if m else ''
        d['consultant_name'] = c.name if c else ''
        # 签到明细
        d['checkins'] = [
            to_dict(ci) for ci in
            db.query(CourseCheckin).filter(CourseCheckin.enrollment_id == e.id).all()
        ]
        # 跟进记录
        d['followups'] = [
            to_dict(f) for f in
            db.query(CourseFollowup).filter(CourseFollowup.enrollment_id == e.id)
            .order_by(desc(CourseFollowup.id)).limit(10).all()
        ]
        result.append(d)
    return ok(result)


@admin_router.post("/{sid}/enrollments")
def admin_create_enrollment(
    sid: int, body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """管理端手动添加报名"""
    cs = db.query(CourseSession).filter(CourseSession.id == sid).first()
    if not cs:
        raise HTTPException(404, "场次不存在")
    member_id = body.get("member_id")
    if not member_id:
        raise HTTPException(400, "缺少 member_id")

    # 检查重复报名
    existing = db.query(CourseEnrollment).filter(
        CourseEnrollment.session_id == sid,
        CourseEnrollment.member_id == member_id,
    ).first()
    if existing:
        raise HTTPException(400, "该会员已报名此场次")

    m = db.query(Member).filter(Member.id == member_id).first()
    enrollment_no = f"CE-{date.today().strftime('%Y%m%d')}-{random.randint(1000,9999)}"
    price_type = body.get("price_type", "normal")
    paid = float(cs.trial_price or 0) if price_type == "trial" else float(cs.normal_price or 0)

    e = CourseEnrollment(
        enrollment_no=enrollment_no,
        session_id=sid,
        member_id=member_id,
        consultant_id=body.get("consultant_id") or (m.consultant_id if m else None),
        service_id=cs.service_id,
        price_type=price_type,
        paid_amount=paid,
        status="enrolled",
    )
    db.add(e)
    cs.enrolled_count = (cs.enrolled_count or 0) + 1
    db.commit()
    db.refresh(e)
    return ok(to_dict(e))


@admin_router.put("/enrollments/{eid}/pay")
def admin_pay_enrollment(
    eid: int, body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """确认付费"""
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == eid).first()
    if not e:
        raise HTTPException(404, "报名记录不存在")
    e.pay_status = "paid"
    e.paid_amount = body.get("amount", e.paid_amount)
    e.payment_id = body.get("payment_id")
    if e.status == "enrolled":
        e.status = "paid"
    db.commit()
    return ok(to_dict(e))


# ============================================================
# 管理端 — 签到
# ============================================================

@admin_router.post("/{sid}/checkin")
def admin_checkin(
    sid: int, body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """扫脸签到（管理端触发）
    body: { member_id, day_number, checkin_type: "face"|"manual", face_score, photo_url }
    """
    member_id = body.get("member_id")
    day_number = body.get("day_number", 1)
    if not member_id:
        raise HTTPException(400, "缺少 member_id")

    # 查报名
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.session_id == sid,
        CourseEnrollment.member_id == member_id,
    ).first()
    if not enrollment:
        m = db.query(Member).filter(Member.id == member_id).first()
        name = m.name if m else f"ID#{member_id}"
        raise HTTPException(400, f"【{name}】未报名此场次")

    # 幂等：同一天不重复签到
    existing = db.query(CourseCheckin).filter(
        CourseCheckin.enrollment_id == enrollment.id,
        CourseCheckin.day_number == day_number,
    ).first()
    if existing:
        return ok({"msg": "今日已签到", "checkin": to_dict(existing)})

    ci = CourseCheckin(
        session_id=sid,
        enrollment_id=enrollment.id,
        member_id=member_id,
        day_number=day_number,
        checkin_type=body.get("checkin_type", "face"),
        face_score=body.get("face_score"),
        photo_url=body.get("photo_url"),
    )
    db.add(ci)

    # 更新报名签到记录
    days = enrollment.checkin_days or []
    days.append({
        "day": day_number,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type": body.get("checkin_type", "face"),
    })
    enrollment.checkin_days = days
    enrollment.checkin_total = len(days)
    if enrollment.status in ("enrolled", "paid"):
        enrollment.status = "checked_in"

    # 更新场次签到数
    cs = db.query(CourseSession).filter(CourseSession.id == sid).first()
    if cs and day_number == 1:  # 首日签到才计入场次签到人数
        cs.checkin_count = (cs.checkin_count or 0) + 1

    db.commit()
    db.refresh(ci)
    return ok(to_dict(ci))


# ============================================================
# 管理端 — 课后跟进
# ============================================================

@admin_router.post("/enrollments/{eid}/followup")
def admin_add_followup(
    eid: int, body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """手动添加跟进记录"""
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == eid).first()
    if not e:
        raise HTTPException(404, "报名记录不存在")

    f = CourseFollowup(
        enrollment_id=eid,
        member_id=e.member_id,
        consultant_id=body.get("consultant_id") or e.consultant_id,
        followup_type=body.get("followup_type", "manual"),
        content=body.get("content", ""),
        result=body.get("result"),
        next_action=body.get("next_action"),
        triggered_by=body.get("triggered_by", "manual"),
    )
    db.add(f)

    e.followup_count = (e.followup_count or 0) + 1
    e.last_followup_at = datetime.utcnow()
    if body.get("result") == "signed":
        e.signed_deal = True
        e.status = "closed"
        e.next_followup_date = None
    else:
        e.next_followup_date = date.today() + timedelta(days=7)

    db.commit()
    return ok(to_dict(f))


@admin_router.put("/enrollments/{eid}/deal")
def admin_mark_deal(
    eid: int, body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """标记现场签单"""
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == eid).first()
    if not e:
        raise HTTPException(404, "报名记录不存在")
    e.signed_deal = True
    e.deal_order_id = body.get("order_id")
    e.status = "closed"
    e.next_followup_date = None
    db.commit()
    return ok(to_dict(e))


# ============================================================
# 管理端 — 结课（手动/自动）
# ============================================================

@admin_router.put("/{sid}/end")
def admin_end_session(
    sid: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    """手动结课"""
    cs = db.query(CourseSession).filter(CourseSession.id == sid).first()
    if not cs:
        raise HTTPException(404, "场次不存在")
    return _end_session(cs, db)


def _end_session(cs: CourseSession, db: Session):
    """结课逻辑：状态变灰 + 自动扣款 + 设置跟进"""
    cs.status = "ended"

    enrollments = db.query(CourseEnrollment).filter(
        CourseEnrollment.session_id == cs.id,
    ).all()

    for e in enrollments:
        # 自动扣款（独立付费，不从套餐扣）
        if e.pay_status == "paid" and e.status != "completed":
            e.status = "completed"

        # 未成交 → 设置7天跟进
        if not e.signed_deal:
            e.status = "follow_up"
            e.next_followup_date = date.today() + timedelta(days=7)

    db.commit()
    return ok({"msg": f"已结课，{len(enrollments)}人完成", "session": to_dict(cs)})


# ============================================================
# 小程序端 — 查看场次 + 报名
# ============================================================

@router.get("")
def list_sessions(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """小程序展示报名中的场次"""
    q = db.query(CourseSession)
    if status:
        q = q.filter(CourseSession.status == status)
    else:
        # 默认只展示报名中和进行中
        q = q.filter(CourseSession.status.in_(["enrolling", "ongoing"]))

    sessions = q.order_by(CourseSession.start_date).all()
    result = []
    for s in sessions:
        d = {
            "id": s.id,
            "session_no": s.session_no,
            "title": s.title,
            "edition": s.edition,
            "city": s.city,
            "venue": s.venue,
            "start_date": str(s.start_date) if s.start_date else None,
            "end_date": str(s.end_date) if s.end_date else None,
            "duration_days": s.duration_days,
            "capacity": s.capacity,
            "enrolled_count": s.enrolled_count,
            "remaining": max(0, (s.capacity or 0) - (s.enrolled_count or 0)),
            "normal_price": float(s.normal_price) if s.normal_price else None,
            "trial_price": float(s.trial_price) if s.trial_price else None,
            "status": s.status,
            "description": s.description,
            "cover_image": s.cover_image,
            "highlights": s.highlights,
        }
        svc = db.query(Service).filter(Service.id == s.service_id).first()
        d['service_name'] = svc.name if svc else ''
        result.append(d)
    return ok(result)


@router.get("/{sid}")
def get_session_detail(sid: int, db: Session = Depends(get_db)):
    """场次详情"""
    cs = db.query(CourseSession).filter(CourseSession.id == sid).first()
    if not cs:
        raise HTTPException(404, "场次不存在")
    d = to_dict(cs)
    svc = db.query(Service).filter(Service.id == cs.service_id).first()
    d['service_name'] = svc.name if svc else ''
    d['remaining'] = max(0, (cs.capacity or 0) - (cs.enrolled_count or 0))
    return ok(d)


@router.post("/{sid}/enroll")
def member_enroll(
    sid: int,
    body: EnrollCreate,
    db: Session = Depends(get_db),
    current: Member = Depends(get_current_member),
):
    """小程序端会员报名"""
    cs = db.query(CourseSession).filter(CourseSession.id == sid).first()
    if not cs:
        raise HTTPException(404, "场次不存在")
    if cs.status != "enrolling":
        raise HTTPException(400, "该场次已停止报名")
    if (cs.enrolled_count or 0) >= (cs.capacity or 0):
        raise HTTPException(400, "名额已满")

    # 防重复
    existing = db.query(CourseEnrollment).filter(
        CourseEnrollment.session_id == sid,
        CourseEnrollment.member_id == current.id,
    ).first()
    if existing:
        raise HTTPException(400, "您已报名此场次")

    price_type = body.price_type or "normal"
    paid = float(cs.trial_price or 0) if price_type == "trial" else float(cs.normal_price or 0)
    enrollment_no = f"CE-{date.today().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

    e = CourseEnrollment(
        enrollment_no=enrollment_no,
        session_id=sid,
        member_id=current.id,
        consultant_id=current.consultant_id,
        service_id=cs.service_id,
        price_type=price_type,
        paid_amount=paid,
        status="enrolled",
    )
    db.add(e)
    cs.enrolled_count = (cs.enrolled_count or 0) + 1
    db.commit()
    db.refresh(e)

    # TODO: 通知归属老师（飞书/企微消息）

    return ok(to_dict(e))


@router.get("/my/enrollments")
def my_enrollments(
    db: Session = Depends(get_db),
    current: Member = Depends(get_current_member),
):
    """我的报名记录"""
    enrollments = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.member_id == current.id)
        .order_by(desc(CourseEnrollment.id))
        .all()
    )
    result = []
    for e in enrollments:
        d = to_dict(e)
        cs = db.query(CourseSession).filter(CourseSession.id == e.session_id).first()
        d['session_title'] = cs.title if cs else ''
        d['session_city'] = cs.city if cs else ''
        d['session_start_date'] = str(cs.start_date) if cs and cs.start_date else ''
        d['session_status'] = cs.status if cs else ''
        result.append(d)
    return ok(result)


# ============================================================
# Webhook — 三和跟进接口
# ============================================================

@webhook_router.post("/followup/pending")
def webhook_pending_followups(db: Session = Depends(get_db)):
    """获取待跟进客户列表（三和Agent定时调用）
    返回 next_followup_date <= today 且未成交的报名记录
    """
    today = date.today()
    pending = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.signed_deal == False,
            CourseEnrollment.status == "follow_up",
            CourseEnrollment.next_followup_date <= today,
        )
        .all()
    )
    result = []
    for e in pending:
        m = db.query(Member).filter(Member.id == e.member_id).first()
        c = db.query(Consultant).filter(Consultant.id == e.consultant_id).first() if e.consultant_id else None
        cs = db.query(CourseSession).filter(CourseSession.id == e.session_id).first()
        result.append({
            "enrollment_id": e.id,
            "member_id": e.member_id,
            "member_name": m.name if m else "",
            "enterprise_name": getattr(m, 'enterprise_name', '') if m else "",
            "member_phone": m.phone if m else "",
            "consultant_id": e.consultant_id,
            "consultant_name": c.name if c else "",
            "session_title": cs.title if cs else "",
            "followup_count": e.followup_count,
            "last_followup": str(e.last_followup_at)[:16] if e.last_followup_at else None,
            "days_since_course": (today - cs.end_date).days if cs and cs.end_date else 0,
        })
    return ok(result)


@webhook_router.post("/followup/report")
def webhook_report_followup(body: dict, db: Session = Depends(get_db)):
    """三和Agent回报跟进结果
    body: { enrollment_id, content, result, next_action, consultant_id }
    """
    eid = body.get("enrollment_id")
    e = db.query(CourseEnrollment).filter(CourseEnrollment.id == eid).first()
    if not e:
        raise HTTPException(404, "报名记录不存在")

    f = CourseFollowup(
        enrollment_id=eid,
        member_id=e.member_id,
        consultant_id=body.get("consultant_id") or e.consultant_id,
        followup_type="agent",
        content=body.get("content", ""),
        result=body.get("result"),
        next_action=body.get("next_action"),
        triggered_by="agent_sanhe",
    )
    db.add(f)

    e.followup_count = (e.followup_count or 0) + 1
    e.last_followup_at = datetime.utcnow()
    if body.get("result") == "signed":
        e.signed_deal = True
        e.status = "closed"
        e.next_followup_date = None
    elif body.get("result") == "rejected":
        e.status = "closed"
        e.next_followup_date = None
    else:
        e.next_followup_date = date.today() + timedelta(days=7)

    db.commit()
    return ok({"msg": "跟进记录已保存", "followup": to_dict(f)})


# ============================================================
# 自动化定时任务（由cron调用）
# ============================================================

@webhook_router.post("/automation/check")
def automation_check(db: Session = Depends(get_db)):
    """定时扫描：T-20/T-10/T-5 提醒 + 自动结课 + 自动开始
    建议cron每天早上9点调一次
    """
    today = date.today()
    actions = []

    sessions = db.query(CourseSession).filter(
        CourseSession.status.in_(["enrolling", "ongoing"])
    ).all()

    for cs in sessions:
        days_to_start = (cs.start_date - today).days if cs.start_date else 999
        days_to_end = (cs.end_date - today).days if cs.end_date else 999

        # T-20: 发调研表提醒
        if days_to_start <= 20 and not cs.survey_sent:
            cs.survey_sent = True
            actions.append({"session": cs.id, "action": "survey_remind", "title": cs.title})
            # TODO: 通知老师发调研表

        # T-10: 订票提醒
        if days_to_start <= 10 and not cs.ticket_remind_sent:
            cs.ticket_remind_sent = True
            actions.append({"session": cs.id, "action": "ticket_remind", "title": cs.title})
            # TODO: 通知老师联系客户订票

        # T-5: 系统通知
        if days_to_start <= 5 and not cs.notify_sent:
            cs.notify_sent = True
            actions.append({"session": cs.id, "action": "notify_sent", "title": cs.title})
            # TODO: 发送小程序/短信通知客户

        # 开课日：自动变为进行中
        if days_to_start <= 0 and cs.status == "enrolling":
            cs.status = "ongoing"
            actions.append({"session": cs.id, "action": "auto_start", "title": cs.title})

        # 结课日：自动结课
        if days_to_end < 0 and cs.status == "ongoing":
            _end_session(cs, db)
            actions.append({"session": cs.id, "action": "auto_end", "title": cs.title})

    db.commit()
    return ok({"date": str(today), "actions": actions})
