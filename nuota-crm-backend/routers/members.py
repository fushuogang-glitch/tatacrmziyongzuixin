# 学员相关
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Member
from models.booking import Consultant
from schemas.api import MemberRegisterIn, MemberOut
from services.referral_service import bind_referral
from utils.auth import get_current_member, create_token, decode_token
from utils.helpers import ok, to_dict, gen_member_no, gen_referral_code
from fastapi.security import OAuth2PasswordBearer
from fastapi import Header


router = APIRouter(prefix="/api/members", tags=["members"])


def _member_out(m: Member, db: Session = None) -> dict:
    data = to_dict(m, [
        "id", "name", "phone", "enterprise_name", "city", "role",
        "member_type", "member_no", "enroll_date", "expire_date",
        "referral_code", "referred_by", "status", "member_tier",
        "consultant_id", "gender", "birthday",
    ])
    data["face_bound"] = bool(m.face_token)
    # 专属顾问信息
    data["advisor_name"] = ""
    data["advisor_phone"] = ""
    if m.consultant_id and db:
        c = db.query(Consultant).filter(Consultant.id == m.consultant_id).first()
        if c:
            data["advisor_name"] = c.name or ""
            data["advisor_phone"] = c.phone or ""
    # 等级体系信息
    TIER_ORDER = [
        ("kindergarten", "七杀星", 1),
        ("primary", "天相星", 2),
        ("junior", "天同星", 3),
        ("senior", "天机星", 4),
        ("college", "天梁星", 5),
        ("bachelor", "天府星", 6),
        ("master", "太阴元君", 7),
        ("doctor", "日曜帝君", 8),
        ("postdoc", "紫微大帝", 9),
    ]
    TIER_REQS = {
        "primary":    {"course": 1, "service": 1, "mixed": 1, "referral": 0},
        "junior":     {"course": 5, "service": 5, "mixed": 8, "referral": 5},
        "senior":     {"course": 8, "service": 8, "mixed": 13, "referral": 8},
        "college":    {"course": 10, "service": 10, "mixed": 15, "referral": 10},
        "bachelor":   {"course": 15, "service": 15, "mixed": 20, "referral": 15},
        "master":     {"course": 20, "service": 20, "mixed": 30, "referral": 20},
        "doctor":     {"course": 25, "service": 25, "mixed": 40, "referral": 25},
        "postdoc":    {"course": 30, "service": 30, "mixed": 50, "referral": 30},
    }
    tier_key = m.member_tier or "kindergarten"
    cur_idx = 0
    for i, (k, n, lv) in enumerate(TIER_ORDER):
        if k == tier_key:
            cur_idx = i
            break
    course_count = 0
    service_count = 0
    referral_count = 0
    history_c = getattr(m, 'history_course_count', 0) or 0
    history_s = getattr(m, 'history_service_count', 0) or 0
    history_r = getattr(m, 'history_referral_count', 0) or 0
    if db:
        from models import Referral
        try:
            from models.course import CourseEnrollment
            course_count = db.query(func.count(CourseEnrollment.id)).filter(
                CourseEnrollment.member_id == m.id,
                CourseEnrollment.status == "completed"
            ).scalar() or 0
        except Exception:
            pass
        try:
            from models.service_order import ServiceOrder
            service_count = db.query(func.count(ServiceOrder.id)).filter(
                ServiceOrder.member_id == m.id,
                ServiceOrder.status == "completed"
            ).scalar() or 0
        except Exception:
            pass
        try:
            referral_count = db.query(func.count(Referral.id)).filter(
                Referral.referrer_id == m.id,
                Referral.status == "confirmed"
            ).scalar() or 0
        except Exception:
            pass
    total_course = course_count + history_c
    total_service = service_count + history_s
    total_referral = referral_count + history_r
    total_mixed = total_course + total_service
    new_tier_idx = 0
    for i in range(len(TIER_ORDER) - 1, 0, -1):
        code = TIER_ORDER[i][0]
        reqs = TIER_REQS.get(code, {})
        hit = False
        if total_course >= reqs.get("course", 999):
            hit = True
        if total_service >= reqs.get("service", 999):
            hit = True
        if reqs.get("mixed", 0) > 0 and total_mixed >= reqs.get("mixed", 999):
            hit = True
        if reqs.get("referral", 0) > 0 and total_referral >= reqs.get("referral", 999):
            hit = True
        if hit:
            new_tier_idx = i
            break
    if new_tier_idx > cur_idx and db:
        cur_idx = new_tier_idx
        m.member_tier = TIER_ORDER[cur_idx][0]
        try:
            db.commit()
        except Exception:
            pass
    cur_code, cur_name, cur_level = TIER_ORDER[cur_idx]
    tier_info = {"tier_key": cur_code, "tier_name": cur_name, "tier_level": cur_level}
    tier_info["stats"] = {
        "course_count": total_course,
        "service_count": total_service,
        "referral_count": total_referral,
        "mixed_count": total_mixed,
    }
    if cur_idx < len(TIER_ORDER) - 1:
        nxt_code, nxt_name, nxt_level = TIER_ORDER[cur_idx + 1]
        tier_info["next_tier"] = {"key": nxt_code, "name": nxt_name, "level": nxt_level}
        reqs = TIER_REQS.get(nxt_code, {})
        tier_info["next_requirements"] = {
            "course": {"current": total_course, "required": reqs.get("course", 0)},
            "service": {"current": total_service, "required": reqs.get("service", 0)},
            "mixed": {"current": total_mixed, "required": reqs.get("mixed", 0)},
            "referral": {"current": total_referral, "required": reqs.get("referral", 0)},
        }
    else:
        tier_info["next_tier"] = None
        tier_info["next_requirements"] = None
    data["tier_info"] = tier_info
    # 顶层统计字段（供小程序直接读取）
    data["referral_count"] = total_referral
    data["referral_income"] = 0  # TODO: 接入实际推荐收入
    data["service_order_count"] = total_service
    data["course_count"] = total_course
    # 合作年限
    if m.enroll_date:
        from datetime import date as _date
        delta = _date.today() - m.enroll_date
        data["cooperation_years"] = max(1, delta.days // 365) if delta.days >= 365 else round(delta.days / 365, 1)
    else:
        data["cooperation_years"] = 0
    # 企业团队人数
    if m.enterprise_name and db:
        data["staff_count"] = db.query(func.count(Member.id)).filter(
            Member.enterprise_name == m.enterprise_name,
            Member.status == "active"
        ).scalar() or 0
    else:
        data["staff_count"] = 0
    return data


def _resolve_referral_code(db: Session, code: str):
    """识别推荐码来源：会员推荐码 or 老师推荐码。
    返回 (source_type, referrer_member, consultant)
    - ('member', Member, None) — 会员老板推荐
    - ('consultant', None, Consultant) — 塔塔老师推荐
    - (None, None, None) — 无效
    """
    if not code:
        return None, None, None
    # 先查会员推荐码
    member = db.query(Member).filter(Member.referral_code == code).first()
    if member:
        return "member", member, None
    # 再查老师推荐码（TATA-XXX格式）
    consultant = db.query(Consultant).filter(Consultant.referral_code == code).first()
    if consultant:
        return "consultant", None, consultant
    return None, None, None


@router.post("/register")
def register(body: MemberRegisterIn, db: Session = Depends(get_db),
             authorization: str | None = Header(default=None)):
    """学员注册。支持三种场景：
    1. 会员老板推荐码 → 新人关联为该老板推荐的客户
    2. 塔塔老师推荐码 → 新人成为该老师的归属客户
    3. 企业邀请码 → 员工加入已有企业
    """
    openid = body.openid
    if not openid and authorization and authorization.lower().startswith("bearer "):
        try:
            payload = decode_token(authorization.split(" ", 1)[1])
            if payload.get("role") == "guest":
                openid = payload.get("openid") or payload.get("sub")
        except Exception:
            openid = None

    exist = db.query(Member).filter(Member.phone == body.phone).first()
    if exist:
        if openid and not exist.openid:
            exist.openid = openid
            db.commit()
        token = create_token(subject=exist.id, role="member", extra={"openid": openid or ""})
        return ok({"token": token, "user": _member_out(exist, db)})

    is_miniapp = bool(openid)

    # ——— 邀请码模式：员工加入企业 ———
    invite = None
    if body.invite_code:
        from models.enterprise import EnterpriseInvite, Enterprise
        from datetime import datetime as _dt
        invite = db.query(EnterpriseInvite).filter(
            EnterpriseInvite.code == body.invite_code.upper(),
            EnterpriseInvite.status == "active",
        ).first()
        if not invite or invite.expires_at < _dt.now() or invite.used_count >= invite.max_uses:
            raise HTTPException(status_code=400, detail="邀请码无效或已过期")
        current_count = db.query(Member).filter(
            Member.enterprise_id == invite.enterprise_id,
            Member.status == "active"
        ).count()
        if current_count >= 10:
            raise HTTPException(status_code=400, detail="该企业团队已满(最多10人)")

    # ——— 推荐码模式：会员推荐 or 老师推荐 ———
    ref_source, ref_member, ref_consultant = None, None, None
    if body.referral_code:
        ref_source, ref_member, ref_consultant = _resolve_referral_code(db, body.referral_code)
        if not ref_source:
            raise HTTPException(status_code=400, detail="推荐码无效，请检查后重新输入")

    # 小程序端必须有推荐码或邀请码
    if is_miniapp and not body.invite_code and not body.referral_code:
        raise HTTPException(status_code=400, detail="请输入推荐码或邀请码")

    m = Member(
        name=body.name,
        phone=body.phone,
        enterprise_name=body.enterprise_name,
        city=body.city,
        role=body.role or "boss",
        member_type=body.member_type or "trial",
        enroll_date=date.today(),
        status="active",
        openid=openid,
    )
    db.add(m)
    db.flush()

    m.member_no = gen_member_no(db)
    m.referral_code = gen_referral_code()

    # ---- 处理推荐码绑定 ----
    if ref_source == "member" and ref_member:
        # 会员老板推荐 → 建立referral关系
        bind_referral(db, m, body.referral_code)
    elif ref_source == "consultant" and ref_consultant:
        # 老师推荐 → 自动绑定归属老师
        m.consultant_id = ref_consultant.id

    # ---- 企业邀请码绑定（员工加入）----
    if invite:
        from models.enterprise import Enterprise
        m.enterprise_id = invite.enterprise_id
        m.role = invite.role
        ent = db.query(Enterprise).filter(Enterprise.id == invite.enterprise_id).first()
        if ent:
            m.enterprise_name = ent.name
        invite.used_count += 1
    # ---- 推荐码 + 创建企业（老板）----
    elif body.create_enterprise and body.enterprise_name:
        from models.enterprise import Enterprise
        ent = Enterprise(
            name=body.enterprise_name,
            city=body.city or "",
            contact_phone=body.phone,
            boss_member_id=m.id,
            status="active",
        )
        db.add(ent)
        db.flush()
        m.enterprise_id = ent.id
        m.role = "boss"

    db.commit()
    db.refresh(m)

    token = create_token(subject=m.id, role="member", extra={"openid": openid or ""})
    return ok({"token": token, "user": _member_out(m, db)})




@router.get("/my-schedules")
def my_schedules(current: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    """返回当前会员的全部排期（工单+下店预约+手动排期）实时同步"""
    from models.service import ServiceOrder, Service
    from models.booking import ConsultantSchedule, VisitBooking
    from datetime import timedelta

    result = []

    status_labels = {
        "pending": "待确认",
        "confirmed": "排期已确认",
        "accepted": "老师已接单",
        "preparing": "执案准备中",
        "in_progress": "执案中",
        "follow_up": "跟进中",
        "completed": "已完成",
        "cancelled": "已取消",
    }

    # ── 1. 专案服务工单 ──
    orders = (
        db.query(ServiceOrder)
        .filter(ServiceOrder.member_id == current.id)
        .filter(ServiceOrder.status.notin_(["cancelled"]))
        .order_by(ServiceOrder.appoint_date.desc())
        .all()
    )
    for o in orders:
        svc = db.query(Service).filter(Service.id == o.service_id).first() if o.service_id else None
        cons = db.query(Consultant).filter(Consultant.id == o.consultant_id).first() if o.consultant_id else None
        days = svc.duration_days if svc and svc.duration_days else 1
        date_start = str(o.appoint_date) if o.appoint_date else ""
        date_end = str(o.appoint_date + timedelta(days=days - 1)) if o.appoint_date else ""
        result.append({
            "id": o.id,
            "type": "service_order",
            "order_no": o.order_no,
            "service_name": svc.name if svc else "",
            "consultant_name": cons.name if cons else "",
            "date_start": date_start,
            "date_end": date_end,
            "days": days,
            "city": o.store_address or "",
            "store_name": o.store_name or "",
            "order_status": o.status,
            "status_label": status_labels.get(o.status, o.status),
            "workflow_stage": o.workflow_stage or "",
            "workflow_progress": o.workflow_progress or 0,
            "appoint_time": o.appoint_time or "",
        })

    # ── 2. 下店预约（bookings） ──
    bookings = (
        db.query(VisitBooking)
        .filter(VisitBooking.member_id == current.id)
        .filter(VisitBooking.status.notin_(["cancelled"]))
        .order_by(VisitBooking.apply_time.desc())
        .all()
    )
    booking_labels = {"pending": "待确认", "confirmed": "已确认", "completed": "已完成"}
    for b in bookings:
        cons = db.query(Consultant).filter(Consultant.id == b.consultant_id).first() if b.consultant_id else None
        b_days = b.duration_days or 2
        b_date = b.confirmed_date or b.preferred_date
        date_start = str(b_date) if b_date else ""
        date_end = str(b_date + timedelta(days=b_days - 1)) if b_date else ""
        result.append({
            "id": b.id,
            "type": "visit_booking",
            "order_no": "",
            "service_name": "下店辅导",
            "consultant_name": cons.name if cons else "待分配",
            "date_start": date_start,
            "date_end": date_end,
            "days": b_days,
            "city": b.city or "",
            "store_name": b.address or "",
            "order_status": b.status,
            "status_label": booking_labels.get(b.status, b.status),
            "workflow_stage": "",
            "workflow_progress": 100 if b.status == "completed" else (50 if b.status == "confirmed" else 10),
            "appoint_time": "",
        })

    # ── 3. 排期表中直接关联本会员的手动排期（老师在CRM录入） ──
    # 通过工单关联：排期.order_id → 工单.member_id = 当前用户
    order_ids = [o.id for o in orders]
    if order_ids:
        manual_schedules = (
            db.query(ConsultantSchedule)
            .filter(
                ConsultantSchedule.order_id.notin_(order_ids),  # 排除已在工单中返回的
                ConsultantSchedule.schedule_type == "busy",
            )
            .all()
        )
    else:
        manual_schedules = []
    # 注：纯手动排期（无order_id）暂不关联到特定客户，后续可扩展

    # 按日期排序（最近的在前）
    result.sort(key=lambda x: x["date_start"] or "0", reverse=True)

    return ok(result)

@router.get("/me")
def me(current: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    return ok(_member_out(current, db))
