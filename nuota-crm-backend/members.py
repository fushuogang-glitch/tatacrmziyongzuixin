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
    # 升级条件：课程/专案/混合(课程+专案)/年推荐 —— 任一项达标即可
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
    # 查当前进度
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
    # 自动重算等级：从高到低检查，找到最高符合的等级
    new_tier_idx = 0  # 默认L1
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
    # 如果算出的等级比当前高，自动升级
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
    # 下一级
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
    return data


@router.post("/register")
def register(body: MemberRegisterIn, db: Session = Depends(get_db),
             authorization: str | None = Header(default=None)):
    """学员注册。允许两种入口：
    - 匿名注册（后台/运营）：直接按 phone 建档；
    - 小程序 guest token 注册：从 token.extra.openid 绑定。
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
        # 已存在：如果 openid 缺失则补齐
        if openid and not exist.openid:
            exist.openid = openid
            db.commit()
        token = create_token(subject=exist.id, role="member", extra={"openid": openid or ""})
        return ok({"token": token, "user": _member_out(exist, db)})

    # ⭐ 小程序注册必须有企业邀请码（后台录入不限制）
    invite = None
    is_miniapp = bool(openid)  # 有openid说明是小程序端
    if body.invite_code:
        from models.enterprise import EnterpriseInvite, Enterprise
        from datetime import datetime as _dt
        invite = db.query(EnterpriseInvite).filter(
            EnterpriseInvite.code == body.invite_code.upper(),
            EnterpriseInvite.status == "active",
        ).first()
        if not invite or invite.expires_at < _dt.now() or invite.used_count >= invite.max_uses:
            raise HTTPException(status_code=400, detail="邀请码无效或已过期")
        # 检查企业人数上限
        current_count = db.query(Member).filter(
            Member.enterprise_id == invite.enterprise_id,
            Member.status == "active"
        ).count()
        if current_count >= 10:
            raise HTTPException(status_code=400, detail="该企业团队已满（最多10人）")
    elif is_miniapp:
        raise HTTPException(status_code=400, detail="注册需要企业邀请码，请联系您的老板或塔塔老师获取")

    m = Member(
        name=body.name,
        phone=body.phone,
        enterprise_name=body.enterprise_name,
        city=body.city,
        role=body.role,
        member_type=body.member_type or "trial",
        enroll_date=date.today(),
        status="active",
        openid=openid,
    )
    db.add(m)
    db.flush()

    # 分配学员编号 / 推荐码
    m.member_no = gen_member_no(db)
    m.referral_code = gen_referral_code()

    # 绑定推荐关系
    bind_referral(db, m, body.referral_code)

    # 企业邀请码绑定
    if invite:
        from models.enterprise import Enterprise
        m.enterprise_id = invite.enterprise_id
        m.role = invite.role
        ent = db.query(Enterprise).filter(Enterprise.id == invite.enterprise_id).first()
        if ent:
            m.enterprise_name = ent.name
        invite.used_count += 1

    db.commit()
    db.refresh(m)

    token = create_token(subject=m.id, role="member", extra={"openid": openid or ""})
    return ok({"token": token, "user": _member_out(m, db)})


@router.get("/me")
def me(current: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    return ok(_member_out(current, db))
