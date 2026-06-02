# 顾问自注册 + 邀请码管理
import hashlib
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Consultant, AdminUser
from models.booking import ConsultantApplication, ConsultantInviteCode
from utils.auth import get_current_admin, get_admin_or_agent, create_token
from utils.helpers import ok

router = APIRouter(prefix="/consultant-auth", tags=["consultant-auth"])
admin_router = APIRouter(prefix="/admin/consultant-auth", tags=["admin-consultant-auth"])


# ──────────────────── 工具函数 ────────────────────

def _gen_consultant_referral_code():
    """TATA-XXXX格式的老师推荐码"""
    return f"TATA-{secrets.token_hex(3).upper()}"


def _auto_match_salary(db: Session, consultant):
    """根据级别自动匹配薪资配置（写入log）"""
    from sqlalchemy import text as _text
    try:
        level = consultant.level or "trainee"
        rule = db.execute(_text(
            "SELECT * FROM salary_configs WHERE level = :lv"
        ), {"lv": level}).mappings().first()
        if rule:
            # 记录匹配日志
            from routers.notifications import push_to_all_admins
            push_to_all_admins(
                db,
                title=f"薪资自动匹配 · {consultant.name}",
                body=f"级别 {level} → 底薪¥{rule.get('base_salary',0)}",
                ntype="system",
            )
    except Exception:
        pass  # 薪资表可能还没有该级别配置


def _auto_match_promotion(db: Session, consultant):
    """根据级别自动关联晋级规则"""
    from sqlalchemy import text as _text
    try:
        level = consultant.level or "trainee"
        rule = db.execute(_text(
            "SELECT * FROM promotion_rules WHERE level = :lv"
        ), {"lv": level}).mappings().first()
        # 规则存在即可，晋级进度由 promotion router 自动计算
    except Exception:
        pass


# ──────────────────── Schemas ────────────────────

class ConsultantRegisterIn(BaseModel):
    name: str
    phone: str
    password: str
    specialty: Optional[str] = None
    company: Optional[str] = None
    service_modules: Optional[List[str]] = None
    city: Optional[str] = None
    id_card_last4: Optional[str] = None    # 身份证后4位
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None


class ConsultantLoginIn(BaseModel):
    phone: str
    password: str


class ReviewIn(BaseModel):
    action: str          # approve / reject
    note: Optional[str] = None
    level: Optional[str] = None         # 审核时指定级别
    position: Optional[str] = None      # 审核时指定岗位
    branch_id: Optional[int] = None     # 审核时指定分公司


class TransferMembersIn(BaseModel):
    from_consultant_id: int
    to_consultant_id: int
    member_ids: Optional[List[int]] = None   # None = 全部转移


# ──────────────────── 工具 ────────────────────

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ──────────────────── 顾问端接口 ────────────────────

@router.post("/register")
def consultant_register(body: ConsultantRegisterIn, db: Session = Depends(get_db)):
    """顾问自助注册 → 进入待审核状态"""
    exist = db.query(ConsultantApplication).filter(
        ConsultantApplication.phone == body.phone
    ).first()
    if exist:
        raise HTTPException(400, "该手机号已提交申请，请等待审核")
    exist_c = db.query(Consultant).filter(Consultant.phone == body.phone).first()
    if exist_c:
        raise HTTPException(400, "该手机号已是注册顾问")

    import json
    app = ConsultantApplication(
        name=body.name,
        phone=body.phone,
        specialty=body.specialty,
        company=body.company,
        service_modules=json.dumps(body.service_modules or [], ensure_ascii=False),
        password_hash=hash_pw(body.password),
        status="pending",
    )
    db.add(app)
    db.commit()

    # 通知所有管理员有新申请
    from routers.notifications import push_to_all_admins
    push_to_all_admins(
        db,
        title=f"新老师注册申请 · {body.name}",
        body=f"{body.name}（{body.company or '未选分公司'}）提交了注册申请，请到『老师审核』处理",
        ntype="application",
        ref_type="consultant_application",
    )
    db.commit()
    return ok({"msg": "申请已提交，等待管理员审核通过后即可登录"})


@router.post("/login")
def consultant_login(body: ConsultantLoginIn, db: Session = Depends(get_db)):
    """顾问登录（审核通过后才能登录）"""
    c = db.query(Consultant).filter(Consultant.phone == body.phone).first()
    if not c:
        raise HTTPException(401, "账号不存在或未审核通过")
    if not c.password_hash:
        raise HTTPException(401, "账号未设置密码，请联系管理员")
    if c.password_hash != hash_pw(body.password):
        raise HTTPException(401, "密码错误")
    if c.status != "active":
        raise HTTPException(403, "账号已停用")

    token = create_token(subject=c.id, role="consultant", extra={"consultant_id": c.id})
    return ok({
        "token": token,
        "consultant": {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "company": c.company,
            "specialty": c.specialty,
        }
    })


# ──────────────────── 管理端接口 ────────────────────

@admin_router.get("/applications")
def list_applications(
    status: Optional[str] = "pending",
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent)
):
    """获取顾问申请列表（合并 consultant_applications + admin_users pending）"""
    # 1. consultant_applications 表
    q = db.query(ConsultantApplication)
    if status:
        q = q.filter(ConsultantApplication.status == status)
    if current_admin.role != "super_admin" and current_admin.company:
        q = q.filter(ConsultantApplication.company == current_admin.company)
    apps = q.order_by(ConsultantApplication.created_at.desc()).all()
    result = [{
        "id": a.id, "name": a.name, "phone": a.phone,
        "specialty": a.specialty, "company": a.company,
        "service_modules": a.service_modules,
        "status": a.status, "review_note": a.review_note,
        "created_at": str(a.created_at),
        "source": "application",
    } for a in apps]

    # 2. admin_users 表中 pending 的记录（统一注册入口来的）
    status_map = {"pending": "pending", "approved": "active", "rejected": "rejected"}
    admin_status = status_map.get(status, status)
    if status in ("pending", "approved", "rejected", "active"):
        aq = db.query(AdminUser)
        if status == "pending":
            aq = aq.filter(AdminUser.status == "pending")
        elif status == "approved" or status == "active":
            aq = aq.filter(AdminUser.role != "super_admin", AdminUser.status == "active")
        elif status == "rejected":
            aq = aq.filter(AdminUser.status == "rejected")
        if current_admin.role != "super_admin" and current_admin.company:
            aq = aq.filter(AdminUser.company == current_admin.company)
        # 排除已存在于 consultant_applications 的手机号
        app_phones = {a.phone for a in apps}
        admin_rows = aq.order_by(AdminUser.created_at.desc()).all()
        for u in admin_rows:
            if u.phone and u.phone not in app_phones:
                result.append({
                    "id": u.id, "name": u.real_name or u.username, "phone": u.phone,
                    "specialty": "", "company": u.company or "",
                    "service_modules": None,
                    "status": status, "review_note": "",
                    "created_at": str(u.created_at),
                    "source": "admin_user",
                })
    return ok(result)


@admin_router.post("/applications/{app_id}/review")
def review_application(
    app_id: int,
    body: ReviewIn,
    source: Optional[str] = "application",
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent)
):
    """审核顾问申请：approve / reject（支持 source=application 或 admin_user）"""
    import json

    if source == "admin_user":
        # 来自 admin_users 表的 pending 用户
        user = db.query(AdminUser).filter(AdminUser.id == app_id).first()
        if not user:
            raise HTTPException(404, "用户不存在")
        if current_admin.role != "super_admin":
            if not current_admin.company or user.company != current_admin.company:
                raise HTTPException(403, "无权审核其他分公司")

        if body.action == "approve":
            user.status = "active"
            user.role = "consultant"
            # 同步创建 consultants 表记录
            exist_c = db.query(Consultant).filter(Consultant.phone == user.phone).first()
            if not exist_c:
                consultant = Consultant(
                    name=user.real_name or user.username,
                    phone=user.phone,
                    company=user.company,
                    password_hash=user.password_hash,
                    status="active",
                    level=body.level or "trainee",
                    position=body.position,
                    branch_id=body.branch_id,
                    referral_code=_gen_consultant_referral_code(),
                )
                db.add(consultant)
                db.flush()
                # 自动匹配薪资配置
                _auto_match_salary(db, consultant)
        elif body.action == "reject":
            user.status = "rejected"
        else:
            raise HTTPException(400, "action 只能是 approve 或 reject")
        db.commit()

        from routers.notifications import push_to_all_admins
        action_text = "已通过" if body.action == "approve" else "已拒绝"
        push_to_all_admins(
            db,
            title=f"老师注册审核 · {user.real_name or user.username} {action_text}",
            body=f"申请人：{user.real_name or user.username}，审核人：{current_admin.real_name or current_admin.username}",
            ntype="application",
        )
        db.commit()
        return ok({"msg": "审核完成", "status": user.status})

    # 默认：consultant_applications 表
    app = db.query(ConsultantApplication).filter(ConsultantApplication.id == app_id).first()
    if not app:
        raise HTTPException(404, "申请不存在")

    # 非超管只能审核本公司
    if current_admin.role != "super_admin":
        if not current_admin.company or app.company != current_admin.company:
            raise HTTPException(403, "无权审核其他分公司的申请")

    if body.action == "approve":
        # 创建正式顾问账号
        modules = json.loads(app.service_modules or "[]")
        consultant = Consultant(
            name=app.name,
            phone=app.phone,
            specialty=app.specialty,
            company=app.company,
            service_modules=json.dumps(modules, ensure_ascii=False),
            password_hash=app.password_hash,
            status="active",
            level=body.level or "trainee",
            position=body.position,
            branch_id=body.branch_id,
            referral_code=_gen_consultant_referral_code(),
        )
        db.add(consultant)
        db.flush()
        # 自动匹配薪资配置
        _auto_match_salary(db, consultant)
        app.status = "approved"
    elif body.action == "reject":
        app.status = "rejected"
    else:
        raise HTTPException(400, "action 只能是 approve 或 reject")

    app.reviewed_by = current_admin.id
    app.review_note = body.note
    app.reviewed_at = datetime.now()
    db.commit()

    # 推送通知给所有管理员
    from routers.notifications import push_to_all_admins
    action_text = "已通过" if body.action == "approve" else "已拒绝"
    push_to_all_admins(
        db,
        title=f"老师注册审核 · {app.name} {action_text}",
        body=f"申请人：{app.name}，所属：{app.company or '未填写'}，审核人：{current_admin.real_name or current_admin.username}",
        ntype="application",
        ref_type="consultant_application",
        ref_id=app.id,
    )
    db.commit()
    return ok({"msg": "审核完成", "status": app.status})


# ──────────────────── 邀请码 ────────────────────

@admin_router.post("/invite-code/{consultant_id}")
def generate_invite_code(
    consultant_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent)
):
    """为顾问生成邀请码（管理员操作）"""
    c = db.query(Consultant).filter(Consultant.id == consultant_id).first()
    if not c:
        raise HTTPException(404, "顾问不存在")

    # 非超管只能给本公司顾问生成
    if current_admin.role != "super_admin":
        if c.company != current_admin.company:
            raise HTTPException(403, "无权为其他分公司顾问生成邀请码")

    code = secrets.token_urlsafe(16)
    invite = ConsultantInviteCode(
        consultant_id=consultant_id,
        code=code,
        max_uses=200,
    )
    db.add(invite)
    db.commit()

    miniapp_url = f"https://api.nuotaai.com/register?ref={code}"
    return ok({
        "code": code,
        "miniapp_url": miniapp_url,
        "consultant_name": c.name,
    })


@admin_router.get("/invite-codes/{consultant_id}")
def list_invite_codes(
    consultant_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent)
):
    codes = db.query(ConsultantInviteCode).filter(
        ConsultantInviteCode.consultant_id == consultant_id
    ).all()
    return ok([{
        "id": c.id, "code": c.code,
        "used_count": c.used_count, "max_uses": c.max_uses,
        "is_active": c.is_active,
        "miniapp_url": f"https://api.nuotaai.com/register?ref={c.code}",
    } for c in codes])


# ──────────────────── 客户转绑 ────────────────────

@admin_router.post("/transfer-members")
def transfer_members(
    body: TransferMembersIn,
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent)
):
    """顾问离职：将客户转绑给新顾问（分公司负责人+超管可操作）"""
    from models import Member
    from models.service import ServiceOrder

    src = db.query(Consultant).filter(Consultant.id == body.from_consultant_id).first()
    dst = db.query(Consultant).filter(Consultant.id == body.to_consultant_id).first()
    if not src or not dst:
        raise HTTPException(404, "顾问不存在")

    # 权限：超管全局；管理员只能操作本公司
    if current_admin.role != "super_admin":
        if src.company != current_admin.company or dst.company != current_admin.company:
            raise HTTPException(403, "只能在本公司内转绑客户")

    # 找需要转绑的会员
    if body.member_ids:
        members = db.query(Member).filter(Member.id.in_(body.member_ids)).all()
    else:
        # 找该顾问归属的所有会员（销售归属）
        members = db.query(Member).filter(
            Member.consultant_id == body.from_consultant_id
        ).all()

    # 只转会员归属（销售关系），不动工单（消耗/执案关系）
    member_count = 0
    for m in members:
        m.consultant_id = body.to_consultant_id
        member_count += 1
    db.commit()

    return ok({
        "msg": f"已将 {member_count} 位会员归属从【{src.name}】转至【{dst.name}】（工单执行人不变）",
        "transferred_members": member_count,
        "from": src.name,
        "to": dst.name,
    })


@admin_router.post("/depart/{consultant_id}")
def consultant_depart(
    consultant_id: int,
    body: dict = None,
    db: Session = Depends(get_db),
    current_admin=Depends(get_admin_or_agent)
):
    """老师离职：数据保留，状态改为 departed，可选自动转绑客户"""
    from models import Member
    from models.service import ServiceOrder
    body = body or {}

    c = db.query(Consultant).filter(Consultant.id == consultant_id).first()
    if not c:
        raise HTTPException(404, "老师不存在")

    if current_admin.role != "super_admin":
        if c.company != current_admin.company:
            raise HTTPException(403, "无权操作其他分公司")

    # 标记离职，数据保留
    c.status = "departed"
    transferred = 0

    # 如果指定了接手人，只转会员归属（销售关系），工单不动（执案关系）
    to_id = body.get("to_consultant_id")
    if to_id:
        dst = db.query(Consultant).filter(Consultant.id == to_id).first()
        if dst:
            # 只转会员归属
            transferred = db.query(Member).filter(
                Member.consultant_id == consultant_id
            ).update({"consultant_id": to_id}, synchronize_session=False)

    db.commit()

    from routers.notifications import push_to_all_admins
    msg = f"{c.name} 已标记离职"
    if to_id and transferred:
        msg += f"，{transferred}位会员归属已转绑（工单执行人不变）"
    push_to_all_admins(db, title="老师离职", body=msg, ntype="system")
    db.commit()

    return ok({"msg": msg, "transferred_orders": transferred})


# ──────────────────── 老师专属看板 ────────────────────

def get_current_consultant(
    token: Optional[str] = Depends(
        __import__('fastapi.security', fromlist=['OAuth2PasswordBearer']).OAuth2PasswordBearer(tokenUrl='/consultant-auth/login')
    ),
    db: Session = Depends(get_db),
):
    from utils.auth import decode_token
    if not token:
        raise HTTPException(401, '未登录')
    payload = decode_token(token)
    if payload.get('role') != 'consultant':
        raise HTTPException(401, '非老师身份')
    consultant_id = int(payload.get('sub', 0))
    c = db.query(Consultant).filter(Consultant.id == consultant_id).first()
    if not c:
        raise HTTPException(401, '老师不存在')
    return c


@router.get('/dashboard')
def consultant_dashboard(
    year: int = None,
    month: int = None,
    db: Session = Depends(get_db),
    current: Consultant = Depends(get_current_consultant),
):
    """老师专属看板"""
    from datetime import date
    from sqlalchemy import func, extract, text
    from models.service import ServiceOrder
    from models.booking import VisitBooking
    from models import Member

    now = date.today()
    y = year or now.year
    m = month or now.month
    cid = current.id

    # 本月下店次数（已完成的 visit_bookings）
    visits_month = db.query(VisitBooking).filter(
        VisitBooking.consultant_id == cid,
        VisitBooking.status == 'completed',
        extract('year', VisitBooking.confirmed_date) == y,
        extract('month', VisitBooking.confirmed_date) == m,
    ).all()

    # 本月下店城市列表
    cities = list({v.city for v in visits_month if v.city})

    # 本月下店天数（按 confirmed_date 去重）
    visit_days = len({v.confirmed_date for v in visits_month if v.confirmed_date})

    # 本月服务工单
    orders_month = db.query(ServiceOrder).filter(
        ServiceOrder.consultant_id == cid,
        extract('year', ServiceOrder.created_at) == y,
        extract('month', ServiceOrder.created_at) == m,
    ).all()

    # 本月服务业绩（已完成工单的套餐金额）
    from models.service import ServicePackage
    completed_order_ids = [o.id for o in orders_month if o.status == 'completed']
    revenue = 0
    if completed_order_ids:
        pkgs = db.query(ServicePackage).filter(
            ServicePackage.member_id.in_([o.member_id for o in orders_month if o.status == 'completed'])
        ).all()
        revenue = float(sum(p.amount or 0 for p in pkgs))

    # 本月服务客户数（本月工单里不重复的 member_id）
    served_member_ids = list({o.member_id for o in orders_month})

    # 本月新客户（本月以前没有工单记录的）
    new_clients = 0
    for mid in served_member_ids:
        prev = db.query(ServiceOrder).filter(
            ServiceOrder.consultant_id == cid,
            ServiceOrder.member_id == mid,
            ServiceOrder.created_at < date(y, m, 1),
        ).first()
        if not prev:
            new_clients += 1

    # 全年履历（年度汇总）
    visits_year = db.query(VisitBooking).filter(
        VisitBooking.consultant_id == cid,
        VisitBooking.status == 'completed',
        extract('year', VisitBooking.confirmed_date) == y,
    ).all()
    year_visit_days = len({v.confirmed_date for v in visits_year if v.confirmed_date})
    year_cities = list({v.city for v in visits_year if v.city})

    # 客户列表（本月服务的客户详情）
    members = db.query(Member).filter(Member.id.in_(served_member_ids)).all() if served_member_ids else []
    member_list = [{
        'id': mem.id, 'name': mem.name, 'phone': mem.phone,
        'enterprise_name': mem.enterprise_name, 'city': mem.city,
        'member_tier': mem.member_tier,
    } for mem in members]

    # 近期下店计划（未来 30 天）
    from datetime import timedelta
    upcoming = db.query(VisitBooking).filter(
        VisitBooking.consultant_id == cid,
        VisitBooking.status.in_(['pending', 'confirmed']),
        VisitBooking.confirmed_date >= now,
        VisitBooking.confirmed_date <= now + timedelta(days=30),
    ).order_by(VisitBooking.confirmed_date).all()
    upcoming_list = [{
        'id': v.id,
        'confirmed_date': str(v.confirmed_date),
        'city': v.city,
        'address': v.address,
        'status': v.status,
        'duration_days': v.duration_days,
    } for v in upcoming]


    # ── 晋级进度 ──
    from models.member import Payment
    promo_progress = None
    try:
        promo_rules = {}
        for pr in db.execute(text("SELECT * FROM promotion_rules ORDER BY sort_order")).mappings().all():
            promo_rules[pr["level"]] = dict(pr)

        cur_rule = promo_rules.get(current.level, {})
        cur_sort = cur_rule.get("sort_order", 0)
        next_rule = None
        for lv, rule in sorted(promo_rules.items(), key=lambda x: x[1]["sort_order"]):
            if rule["sort_order"] == cur_sort + 1:
                next_rule = rule
                break

        if next_rule:
            first_of_year = date(y, 1, 1)
            end_of_year = date(y + 1, 1, 1)
            yr_sales = float(db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
                Payment.consultant_id == cid, Payment.pay_status == "completed",
                Payment.created_at >= first_of_year, Payment.created_at < end_of_year,
            ).scalar() or 0)
            yr_work_days = db.query(func.count(func.distinct(ServiceOrder.appoint_date))).filter(
                ServiceOrder.consultant_id == cid,
                ServiceOrder.appoint_date >= first_of_year, ServiceOrder.appoint_date < end_of_year,
                ServiceOrder.status.notin_(["cancelled", "rejected"]),
            ).scalar() or 0
            mentee_count = db.query(func.count(Consultant.id)).filter(
                Consultant.mentor_id == cid, Consultant.status == "active"
            ).scalar() or 0

            t_sales = float(next_rule.get("sales_target", 0))
            t_days = next_rule.get("min_work_days", 0)
            t_mentees = next_rule.get("min_mentees", 0)

            promo_progress = {
                "current_level": current.level,
                "current_level_name": cur_rule.get("level_name", current.level),
                "next_level": next_rule["level"],
                "next_level_name": next_rule["level_name"],
                "year": y,
                "sales": {"actual": yr_sales, "target": t_sales, "gap": max(0, t_sales - yr_sales)},
                "work_days": {"actual": yr_work_days, "target": t_days, "gap": max(0, t_days - yr_work_days)},
                "mentees": {"actual": mentee_count, "target": t_mentees, "gap": max(0, t_mentees - mentee_count)},
            }
        else:
            promo_progress = {
                "current_level": current.level,
                "current_level_name": cur_rule.get("level_name", current.level),
                "next_level": None,
                "next_level_name": "已达最高级",
                "year": y,
            }
    except Exception as e:
        import traceback; traceback.print_exc()
        promo_progress = None

    return ok({
        'consultant': {
            'id': current.id, 'name': current.name,
            'company': current.company, 'specialty': current.specialty,
        },
        'month_stats': {
            'year': y, 'month': m,
            'visit_days': visit_days,           # 本月出差天数
            'visit_cities': cities,              # 本月去过的城市
            'visit_stores': len(visits_month),   # 本月下店次数
            'order_count': len(orders_month),    # 本月服务工单数
            'revenue': revenue,                  # 本月业绩
            'served_clients': len(served_member_ids),  # 服务客户数
            'new_clients': new_clients,          # 新客户数
        },
        'year_stats': {
            'year': y,
            'visit_days': year_visit_days,
            'visit_cities': year_cities,
        },
        'upcoming_visits': upcoming_list,
        'month_clients': member_list,
        'promotion_progress': promo_progress,
    })
