# 管理后台：学员 / 顾问 / 缴费 / 看板
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, extract, text
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Member, Payment, Session as SessionModel, Enrollment,
    Referral, VisitReward, VisitBooking, Consultant, AdminUser,
    ServiceOrder, ServicePackage, PaymentService,
)
from models.booking import ConsultantSchedule
from models.service import Service
from routers.courses import CourseEnrollment
from models.branch import Branch
from schemas.api import (
    MemberRegisterIn, MemberUpdateIn, PaymentCreateIn, ConsultantIn,
)
from services.referral_service import bind_referral, confirm_referral_on_payment
from services.notify_service import notify_referral_reward
from utils.auth import get_current_admin, get_admin_or_agent, get_current_admin_or_consultant
from utils.helpers import ok, to_dict, gen_member_no, gen_referral_code
from routers.members import _member_out


router = APIRouter(prefix="/admin", tags=["admin"])


def log_operation(db: Session, admin: AdminUser, action: str, target_type: str = None, target_id: int = None, detail: str = None):
    """记录操作日志"""
    try:
        db.execute(text("""
            INSERT INTO operation_logs (admin_id, admin_name, action, target_type, target_id, detail)
            VALUES (:aid, :aname, :action, :ttype, :tid, :detail)
        """), {
            'aid': admin.id, 'aname': admin.username,
            'action': action, 'ttype': target_type,
            'tid': target_id, 'detail': detail
        })
        db.commit()
    except Exception:
        pass


def require_super_admin(current: AdminUser = Depends(get_admin_or_agent)):
    """仅超级管理员可操作"""
    if getattr(current, 'role', 'admin') != 'super_admin':
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current


def check_company_permission(admin: AdminUser, target_company: str):
    """管理员只能修改本公司数据"""
    role = getattr(admin, 'role', 'admin')
    if role == 'super_admin':
        return True
    admin_company = getattr(admin, 'company', None)
    if not admin_company or admin_company != target_company:
        raise HTTPException(status_code=403, detail="只能修改本公司数据")
    return True


# ---------- 学员管理 ----------
@router.get("/members")
def list_members(
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
    q: Optional[str] = None, member_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    query = db.query(Member)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Member.name.ilike(like)) | (Member.phone.ilike(like)) |
            (Member.member_no.ilike(like)) | (Member.enterprise_name.ilike(like))
        )
    if member_type:
        query = query.filter(Member.member_type == member_type)
    if status:
        query = query.filter(Member.status == status)

    total = query.count()
    rows = query.order_by(Member.id.desc()).offset((page - 1) * size).limit(size).all()
    return ok({
        "total": total, "page": page, "size": size,
        "items": [to_dict(m) for m in rows],
    })


@router.get("/members/by-tier")
def members_by_tier(db: Session = Depends(get_db),
                   _: AdminUser = Depends(get_admin_or_agent)):
    """按等级分组，返回每级学员列表"""
    TIER_ORDER = [
        ("kindergarten", "七杀星·南斗度厄", 1, ["初始注册权益"]),
        ("primary", "天相星·南斗司禄", 2, ["初次听课/服务权益"]),
        ("junior", "天同星·南斗益算", 3, ["线上会议室问答", "排期优先于三级之前"]),
        ("senior", "天机星·南斗上生", 4, ["线上会议室问答", "排期优先于四级之前", "特殊课程/服务优先获得"]),
        ("college", "天梁星·南斗延寿", 5, ["线上会议室问答", "排期优先于五级之前", "特殊课程/服务优先获得", "合伙人级服务优先选择"]),
        ("bachelor", "天府星·南斗司命", 6, ["线上会议室问答", "排期优先于六级之前", "特殊课程/服务优先获得", "合伙人级服务优先选择"]),
        ("master", "太阴元君·月宫", 7, ["线上会议室问答", "排期优先于七级之前", "特殊课程/服务优先获得", "付老师及合伙人服务优先", "付老师每年亲自指导1次战略规划"]),
        ("doctor", "太阳帝君·日宫", 8, ["线上会议室问答", "排期优先于八级之前", "特殊课程/服务优先获得", "付老师及合伙人服务优先", "付老师每年亲自指导1次战略规划"]),
        ("postdoc", "紫微大帝·中天北极", 9, ["线上会议室问答", "排期优先于所有级别", "特殊课程/服务优先获得", "付老师及合伙人服务优先", "付老师每年亲自指导2次战略规划"]),
    ]
    all_members = db.query(Member).order_by(Member.id.desc()).all()
    tier_map: dict = {}
    for m in all_members:
        t = m.member_tier or "kindergarten"
        if t not in tier_map:
            tier_map[t] = []
        c_name = None
        if m.consultant_id:
            c = db.query(Consultant).filter(Consultant.id == m.consultant_id).first()
            if c:
                c_name = c.name
        tier_map[t].append({
            "id": m.id,
            "member_no": m.member_no,
            "name": m.name,
            "phone": m.phone,
            "enterprise_name": m.enterprise_name,
            "city": m.city,
            "member_type": m.member_type,
            "status": m.status,
            "consultant_name": c_name,
        })
    result = []
    for code, name, level, benefits in TIER_ORDER:
        members = tier_map.get(code, [])
        result.append({
            "tier_code": code,
            "tier_name": name,
            "tier_level": level,
            "benefits": benefits,
            "count": len(members),
            "members": members,
        })
    return ok(result)


@router.post("/members")
def create_member(body: MemberRegisterIn, db: Session = Depends(get_db),
                  _: AdminUser = Depends(get_admin_or_agent)):
    if db.query(Member).filter(Member.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="手机号已存在")
    m = Member(
        name=body.name, phone=body.phone,
        enterprise_name=body.enterprise_name, city=body.city, role=body.role,
        member_type=body.member_type or "trial",
        store_count=body.store_count or 1,
        store_type=body.store_type,
        pre_annual_revenue=body.pre_annual_revenue,
        consultant_id=body.consultant_id,
        gender=body.gender or "female",
        birthday=body.birthday,
        history_course_count=body.history_course_count or 0,
        history_service_count=body.history_service_count or 0,
        history_referral_count=body.history_referral_count or 0,
        enroll_date=date.today(), status="active",
    )
    db.add(m)
    db.flush()
    m.member_no = gen_member_no(db)
    m.referral_code = gen_referral_code()
    bind_referral(db, m, body.referral_code)
    db.commit()
    db.refresh(m)

    # 如果首次录入时填了付款金额，同步创建缴费记录
    if body.first_payment_amount and body.first_payment_amount > 0:
        due_d = None
        if body.first_payment_due_date:
            try:
                due_d = date.fromisoformat(body.first_payment_due_date)
            except Exception:
                pass
        p = Payment(
            member_id=m.id,
            consultant_id=body.consultant_id,
            amount=body.first_payment_amount,
            debt_amount=body.first_payment_debt or 0,
            pay_mode=body.first_payment_mode or "full",
            pay_method=body.first_payment_method,
            pay_type=body.member_type or "annual",
            pay_status="paid" if (body.first_payment_debt or 0) == 0 else "partial",
            pay_time=datetime.utcnow(),
            due_date=due_d,
            remark=body.first_payment_remark,
        )
        db.add(p)
        if body.member_type == "annual":
            m.member_type = "annual"
        db.commit()

    return ok(to_dict(m))


@router.put("/members/{mid}")
def update_member(mid: int, body: MemberUpdateIn, db: Session = Depends(get_db),
                  _: AdminUser = Depends(get_admin_or_agent)):
    m = db.query(Member).filter(Member.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="学员不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    # 触发等级重算并返回完整tier_info
    return ok(_member_out(m, db))


@router.get("/members/{mid}")
def member_detail(mid: int, db: Session = Depends(get_db),
                  _: AdminUser = Depends(get_admin_or_agent)):
    m = db.query(Member).filter(Member.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="学员不存在")
    return ok(_member_out(m, db))


@router.delete("/members/{mid}")
def delete_member(mid: int, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(get_admin_or_agent)):
    m = db.query(Member).filter(Member.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="学员不存在")
    # 快照存入回收站
    import json as _json
    snapshot = to_dict(m)
    db.execute(text(
        "INSERT INTO recycle_bin(target_type,target_id,target_name,snapshot,deleted_by,deleted_by_name) "
        "VALUES(:tt,:tid,:tn,:snap,:dby,:dbn)"
    ), {"tt": "member", "tid": mid, "tn": m.name or "",
        "snap": _json.dumps(snapshot, default=str, ensure_ascii=False),
        "dby": admin.id, "dbn": admin.username})
    # 操作日志
    db.execute(text(
        "INSERT INTO operation_logs(admin_id,admin_name,action,target_type,target_id,detail) "
        "VALUES(:aid,:aname,:act,:tt,:tid,:det)"
    ), {"aid": admin.id, "aname": admin.username, "act": "删除",
        "tt": "客户", "tid": mid, "det": f"删除客户「{m.name}」"})
    # 清除所有关联数据
    related_tables = [
        ("payments", "member_id"),
        ("enrollments", "member_id"),
        ("checkins", "member_id"),
        ("referrals", "referrer_id"),
        ("referrals", "referee_id"),
        ("handbooks", "member_id"),
        ("service_packages", "member_id"),
        ("user_agreements", "member_id"),
        ("visit_rewards", "member_id"),
        ("service_orders", "member_id"),
        ("visit_bookings", "member_id"),
        ("follow_ups", "member_id"),
        ("enterprise_staff", "member_id"),
    ]
    for tbl, col in related_tables:
        try:
            db.execute(text(f"DELETE FROM {tbl} WHERE {col} = :mid"), {"mid": mid})
        except Exception:
            pass
    db.execute(text("UPDATE members SET referred_by = NULL WHERE referred_by = :mid"), {"mid": mid})
    db.delete(m)
    db.commit()
    return ok({"deleted": mid})


# ---------- 缴费 ----------
@router.post("/payments")
def create_payment(body: PaymentCreateIn, db: Session = Depends(get_db),
                   _: AdminUser = Depends(get_admin_or_agent)):
    m = db.query(Member).filter(Member.id == body.member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="学员不存在")

    # 如果未指定归属老师，自动继承学员的归属老师
    cid = body.consultant_id or m.consultant_id
    p = Payment(
        member_id=body.member_id,
        service_id=body.service_id,
        consultant_id=cid,
        amount=body.amount,
        debt_amount=body.debt_amount or 0,
        pay_mode=body.pay_mode or "full",
        pay_method=body.pay_method,
        pay_type=body.pay_type,
        pay_status=body.pay_status,
        pay_time=datetime.strptime(body.pay_date, "%Y-%m-%d") if body.pay_date else (datetime.utcnow() if body.pay_status in ("paid", "partial") else None),
        due_date=date.fromisoformat(body.due_date) if body.due_date else None,
        receipt_image=body.receipt_image,
        remark=body.remark,
    )
    db.add(p)
    db.flush()  # 获取 p.id

    # ── 写入 payment_services 关联表（多选合作项目）──
    all_sids = []
    if body.service_ids:
        all_sids = [int(sid) for sid in body.service_ids if sid]
    elif body.service_id:
        all_sids = [body.service_id]
    for sid in all_sids:
        db.add(PaymentService(payment_id=p.id, service_id=sid))
    # 兼容：service_id 存第一个
    if all_sids and not p.service_id:
        p.service_id = all_sids[0]
    db.flush()

    # ── auto_create_package: 自动创建/关联 ServicePackage ──
    # 年费制：年费总额 / 服务次数 = 每次扣费额
    # 单次制：实际费用 / 专案次数 = 每次扣费额
    if body.pay_status in ("paid", "partial") and body.amount and body.amount > 0:
        pkg = None
        if body.pay_type == "annual":
            total = body.total_times or 6  # 默认6次
            pkg_no = f"PKG-{datetime.now().strftime('%Y%m%d')}-{p.id:04d}"
            per_fee = round(float(body.amount) / total, 2)
            pkg = ServicePackage(
                member_id=m.id,
                package_no=pkg_no,
                total_times=total,
                used_times=0,
                amount=body.amount,
                per_time_fee=per_fee,
                pay_type="annual",
                start_date=date.today(),
                expire_date=date.today().replace(year=date.today().year + 1),
                status="active",
                remark=f"年费套餐 {total}次 × {per_fee}元/次",
            )
            db.add(pkg)
            db.flush()
            p.package_id = pkg.id
        elif body.pay_type in ("single", "trial") and body.service_id:
            svc = db.query(Service).filter(Service.id == body.service_id).first()
            if svc:
                times = svc.total_times or 1
                pkg_no = f"PKG-{datetime.now().strftime('%Y%m%d')}-{p.id:04d}"
                per_fee = round(float(body.amount) / times, 2)
                pkg = ServicePackage(
                    member_id=m.id,
                    package_no=pkg_no,
                    total_times=times,
                    used_times=0,
                    amount=body.amount,
                    per_time_fee=per_fee,
                    pay_type="single",
                    start_date=date.today(),
                    status="active",
                    remark=f"{svc.name} 单次购买 {times}次 × {per_fee}元/次",
                )
                db.add(pkg)
                db.flush()
                p.package_id = pkg.id

    # 同步更新学员归属老师（如果提供了）
    if body.consultant_id and body.consultant_id != m.consultant_id:
        m.consultant_id = body.consultant_id

    if body.pay_status in ("paid", "partial"):
        if body.pay_type == "annual":
            m.member_type = "annual"
            m.enroll_date = m.enroll_date or date.today()

        reward = confirm_referral_on_payment(db, m.id)
        db.commit()
        if reward:
            ref_member = db.query(Member).filter(Member.id == reward.member_id).first()
            if ref_member:
                notify_referral_reward(ref_member.name or "", ref_member.phone or "")
    else:
        db.commit()

    db.refresh(p)
    return ok(to_dict(p))


@router.get("/payments")
def list_payments(
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    q = db.query(Payment)
    if member_id:
        q = q.filter(Payment.member_id == member_id)
    payments = q.order_by(Payment.id.desc()).limit(500).all()

    # 关联查询学员和老师名称
    member_ids = list({p.member_id for p in payments if p.member_id})
    # 收集归属顾问ID（从member取）
    _members_for_cids = {m.id: m for m in db.query(Member).filter(Member.id.in_(list({p.member_id for p in payments if p.member_id}))).all()} if payments else {}
    consultant_ids = list({_members_for_cids[p.member_id].consultant_id for p in payments if p.member_id and p.member_id in _members_for_cids and _members_for_cids[p.member_id].consultant_id})
    members_map = {m.id: m for m in db.query(Member).filter(Member.id.in_(member_ids)).all()} if member_ids else {}
    consultants_map = {c.id: c for c in db.query(Consultant).filter(Consultant.id.in_(consultant_ids)).all()} if consultant_ids else {}

    # 关联分公司
    from models.branch import Branch
    branch_ids = list({p.branch_id for p in payments if p.branch_id})
    branch_map = {}
    if branch_ids:
        brs = db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
        branch_map = {b.id: b.short_name or b.name for b in brs}

    # 关联合作项目（支持多选）
    payment_ids = [p.id for p in payments]
    ps_rows = db.query(PaymentService).filter(PaymentService.payment_id.in_(payment_ids)).all() if payment_ids else []
    # payment_id -> [service_id, ...]
    ps_map = {}
    for ps in ps_rows:
        ps_map.setdefault(ps.payment_id, []).append(ps.service_id)
    # 收集所有 service_id（含旧的单选字段）
    all_service_ids = set()
    for p in payments:
        if p.service_id:
            all_service_ids.add(p.service_id)
        for sid in ps_map.get(p.id, []):
            all_service_ids.add(sid)
    service_map = {}
    if all_service_ids:
        svcs = db.query(Service).filter(Service.id.in_(list(all_service_ids))).all()
        service_map = {s.id: s for s in svcs}

    # 关联套餐（扣费明细）
    package_ids = list({p.package_id for p in payments if p.package_id})
    package_map = {}
    if package_ids:
        pkgs = db.query(ServicePackage).filter(ServicePackage.id.in_(package_ids)).all()
        package_map = {pk.id: pk for pk in pkgs}

    result = []
    for p in payments:
        d = to_dict(p)
        m = members_map.get(p.member_id)
        # 收款归属 = 客户归属顾问（member.consultant_id），而非录入人
        c = consultants_map.get(m.consultant_id) if m and m.consultant_id else None
        d['member_name'] = m.name if m else ''
        d['enterprise_name'] = getattr(m, 'enterprise_name', '') if m else ''
        d['member_phone'] = m.phone if m else ''
        d['consultant_name'] = c.name if c else ''
        d['branch_name'] = branch_map.get(p.branch_id, '') if p.branch_id else ''
        # 多选合作项目
        sids = ps_map.get(p.id, [])
        if not sids and p.service_id:
            sids = [p.service_id]
        svc_names = [service_map[sid].name for sid in sids if sid in service_map]
        svc_categories = [service_map[sid].category for sid in sids if sid in service_map]
        d['service_name'] = ' + '.join(svc_names) if svc_names else ''
        d['service_names'] = svc_names
        d['service_categories'] = svc_categories
        d['service_ids'] = sids
        # 套餐扣费明细
        pkg = package_map.get(p.package_id) if p.package_id else None
        if pkg:
            d['package_id'] = pkg.id
            d['package_no'] = pkg.package_no
            d['total_times'] = pkg.total_times
            d['used_times'] = pkg.used_times or 0
            d['remaining_times'] = (pkg.total_times or 0) - (pkg.used_times or 0)
            d['per_time_fee'] = float(pkg.per_time_fee) if pkg.per_time_fee else 0
            d['pay_type_label'] = '年费制' if (getattr(pkg, 'pay_type', '') or '') == 'annual' else '单次制'
        else:
            d['package_id'] = None
            d['package_no'] = None
            d['total_times'] = None
            d['used_times'] = None
            d['remaining_times'] = None
            d['per_time_fee'] = None
            d['pay_type_label'] = None
        result.append(d)
    return ok(result)


# ---------- 删除缴费记录（仅超级管理员）----------
@router.delete("/payments/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db),
                   admin: AdminUser = Depends(get_current_admin)):
    if admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="仅超级管理员可删除缴费记录")
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="缴费记录不存在")
    # 删除关联的 payment_services
    db.query(PaymentService).filter(PaymentService.payment_id == payment_id).delete()
    # 删除关联的套餐
    if p.package_id:
        pkg = db.query(ServicePackage).filter(ServicePackage.id == p.package_id).first()
        if pkg:
            db.delete(pkg)
    db.delete(p)
    db.commit()
    return ok({"deleted": payment_id})


# ---------- 顾问 ----------
@router.get("/consultants")
def list_consultants(db: Session = Depends(get_db),
                     _: AdminUser = Depends(get_admin_or_agent)):
    from models.branch import Branch
    rows = db.query(Consultant).order_by(Consultant.id.asc()).all()
    # 批量查分公司名
    branch_ids = list({c.branch_id for c in rows if c.branch_id})
    branch_map = {}
    if branch_ids:
        branches = db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
        branch_map = {b.id: b.short_name or b.name for b in branches}
    # 批量查推荐人/带教人名
    all_ids = list({c.id for c in rows})
    name_map = {c.id: c.name for c in rows}
    result = []
    for c in rows:
        d = to_dict(c)
        d['branch_name'] = branch_map.get(c.branch_id, '') if c.branch_id else ''
        d['referrer_name'] = name_map.get(c.referrer_id, '') if c.referrer_id else ''
        d['mentor_name'] = name_map.get(c.mentor_id, '') if c.mentor_id else ''
        # 解析 service_modules JSON → service_ids 列表
        import json as _j
        try:
            d['service_ids'] = _j.loads(c.service_modules) if c.service_modules else []
        except Exception:
            d['service_ids'] = []
        result.append(d)
    return ok(result)


@router.post("/consultants")
def create_consultant(body: ConsultantIn, db: Session = Depends(get_db),
                      current: AdminUser = Depends(get_admin_or_agent)):
    # 管理员只能新增本公司顾问
    role = getattr(current, 'role', 'admin')
    if role != 'super_admin':
        admin_company = getattr(current, 'company', None)
        if not admin_company or body.company != admin_company:
            raise HTTPException(status_code=403, detail="只能新增本公司顾问")
    data = body.model_dump()
    # service_ids → service_modules JSON
    sids = data.pop('service_ids', None)
    if sids is not None:
        import json as _j
        data['service_modules'] = _j.dumps(sids)
    c = Consultant(**data)
    # 自动生成老师推荐码 TATA-XXX
    if not c.referral_code:
        import random, string
        while True:
            suffix = ''.join(random.choices(string.ascii_uppercase, k=3))
            code = f'TATA-{suffix}'
            exist = db.query(Consultant).filter(Consultant.referral_code == code).first()
            if not exist:
                c.referral_code = code
                break
    db.add(c)
    db.commit()
    db.refresh(c)
    log_operation(db, current, '新增顾问', 'consultant', c.id, f'姓名:{c.name} 公司:{c.company}')
    return ok(to_dict(c))


@router.put("/consultants/{cid}")
def update_consultant(cid: int, body: ConsultantIn, db: Session = Depends(get_db),
                      current: AdminUser = Depends(get_admin_or_agent)):
    c = db.query(Consultant).filter(Consultant.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="顾问不存在")
    # 权限检查：管理员只能改本公司顾问
    check_company_permission(current, c.company or '')
    old_info = f'姓名:{c.name} 公司:{c.company}'
    data = body.model_dump()
    sids = data.pop('service_ids', None)
    if sids is not None:
        import json as _j
        data['service_modules'] = _j.dumps(sids)
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    log_operation(db, current, '修改顾问', 'consultant', c.id, f'原:{old_info} 新:姓名:{c.name}')
    return ok(to_dict(c))


@router.delete("/consultants/{cid}")
def delete_consultant(cid: int, db: Session = Depends(get_db),
                      current: AdminUser = Depends(get_admin_or_agent)):
    c = db.query(Consultant).filter(Consultant.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="顾问不存在")
    check_company_permission(current, c.company or '')
    name = c.name
    c.status = 'inactive'
    db.commit()
    log_operation(db, current, '停用顾问', 'consultant', cid, f'姓名:{name}')
    return ok({'msg': '已停用'})


# ---------- 老师排期 ----------
@router.get("/schedules")
def list_schedules(
    consultant_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    _ = Depends(get_current_admin_or_consultant),
):
    q = db.query(ConsultantSchedule)
    if consultant_id:
        q = q.filter(ConsultantSchedule.consultant_id == consultant_id)
    if year:
        q = q.filter(extract('year', ConsultantSchedule.schedule_date) == year)
    if month:
        q = q.filter(extract('month', ConsultantSchedule.schedule_date) == month)
    rows = q.order_by(ConsultantSchedule.schedule_date).all()

    consultant_ids = list({r.consultant_id for r in rows if r.consultant_id})
    c_map = {c.id: c for c in db.query(Consultant).filter(Consultant.id.in_(consultant_ids)).all()} if consultant_ids else {}

    result = []
    for r in rows:
        d = to_dict(r)
        c = c_map.get(r.consultant_id)
        d['consultant_name'] = c.name if c else ''
        result.append(d)
    return ok(result)


@router.post("/schedules")
def create_schedule(
    body: dict,
    db: Session = Depends(get_db),
    current = Depends(get_current_admin_or_consultant),
):
    cid = body.get('consultant_id')
    if current.is_consultant:
        cid = current.consultant_id  # 老师只能给自己录
    s = ConsultantSchedule(
        consultant_id=cid,
        schedule_date=date.fromisoformat(body['schedule_date']),
        city=body.get('city', ''),
        schedule_type=body.get('schedule_type', 'available'),
        title=body.get('title', ''),
        remark=body.get('remark', ''),
        order_id=body.get('order_id'),
        created_by=current.user_id,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return ok(to_dict(s))


@router.post("/schedules/batch")
def batch_create_schedule(
    body: dict,
    db: Session = Depends(get_db),
    current = Depends(get_current_admin_or_consultant),
):
    """批量新增排期：传入 dates 数组一次新增多天
    当 schedule_type=busy 且未关联工单时，自动创建服务工单
    """
    cid = body.get('consultant_id')
    if current.is_consultant:
        cid = current.consultant_id
    dates = body.get('dates', [])
    stype = body.get('schedule_type', 'available')
    order_id = body.get('order_id')
    assistant_id = body.get('assistant_id')  # 助理老师
    member_id = body.get('member_id')        # 客户/会员
    service_id = body.get('service_id')      # 服务项目

    # -- 客户冲突检测：同一客户同时间不能约两个不同老师 --
    if member_id and dates and stype == "busy":
        from models.service import ServiceOrder as SO2
        for d_str in dates:
            conflict = (
                db.query(SO2)
                .join(ConsultantSchedule, (ConsultantSchedule.order_id == SO2.id) & (ConsultantSchedule.schedule_date == date.fromisoformat(d_str)))
                .filter(
                    SO2.member_id == member_id,
                    SO2.consultant_id != cid,
                    SO2.status.notin_(["cancelled", "completed"]),
                )
                .first()
            )
            if conflict:
                c_name = ""
                c_obj = db.query(Consultant).filter(Consultant.id == conflict.consultant_id).first()
                if c_obj:
                    c_name = c_obj.name
                raise HTTPException(400, f"客户在 {d_str} 已由老师 {c_name} 服务(工单#{conflict.id}), 不可同时预约其他老师")

    # 如果是 busy 排期且没关联工单 → 自动创建工单
    auto_order = None
    if stype == 'busy' and not order_id and dates:
        from models.service import ServiceOrder
        order_no = f"SO-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
        first_date = min(dates)
        auto_order = ServiceOrder(
            order_no=order_no,
            member_id=member_id or None,
            service_id=service_id,
            consultant_id=cid,
            assistant_id=assistant_id,
            store_name=body.get('city', '') or body.get('title', ''),
            appoint_date=date.fromisoformat(first_date),
            appoint_time='',
            status='confirmed',
            workflow_stage='已确认·排期自动创建',
            workflow_progress=12,
            remark=f"由排期自动创建，{len(dates)}天，{body.get('title', '')}",
        )
        db.add(auto_order)
        db.flush()  # 获取 auto_order.id
        order_id = auto_order.id

        # 添加系统日志
        from models.service import ServiceWorkLog
        consultant = db.query(Consultant).filter(Consultant.id == cid).first()
        asst = db.query(Consultant).filter(Consultant.id == assistant_id).first() if assistant_id else None
        log_content = f"工单由排期自动创建\n主案老师：{consultant.name if consultant else cid}"
        if asst:
            log_content += f"\n助理老师：{asst.name}"
        log_content += f"\n执案日期：{', '.join(sorted(dates))}\n地点：{body.get('city', '')} {body.get('title', '')}"
        db.add(ServiceWorkLog(
            order_id=auto_order.id, stage='系统', content=log_content, log_type='system',
        ))

        # 通知主案老师
        try:
            from routers.notifications import push_notification
            if consultant:
                push_notification(db, 'consultant', consultant.id,
                    f'新工单已自动创建（主案）',
                    f'{body.get("title", "")}，日期：{", ".join(sorted(dates))}',
                    'order', 'service_order', auto_order.id)
            if asst:
                push_notification(db, 'consultant', asst.id,
                    f'新工单已自动创建（助理）',
                    f'主案：{consultant.name if consultant else ""}，日期：{", ".join(sorted(dates))}',
                    'order', 'service_order', auto_order.id)
        except Exception:
            pass

    # 创建排期记录（主案老师）
    created = []
    for d_str in dates:
        exist = db.query(ConsultantSchedule).filter(
            ConsultantSchedule.consultant_id == cid,
            ConsultantSchedule.schedule_date == date.fromisoformat(d_str),
        ).first()
        if exist:
            if not exist.order_id and order_id:
                exist.order_id = order_id
            continue
        s = ConsultantSchedule(
            consultant_id=cid,
            schedule_date=date.fromisoformat(d_str),
            city=body.get('city', ''),
            schedule_type=stype,
            title=body.get('title', ''),
            remark=body.get('remark', ''),
            order_id=order_id,
            created_by=current.user_id,
        )
        db.add(s)
        created.append(d_str)

    # 助理老师也创建排期
    asst_created = []
    if assistant_id:
        for d_str in dates:
            exist = db.query(ConsultantSchedule).filter(
                ConsultantSchedule.consultant_id == assistant_id,
                ConsultantSchedule.schedule_date == date.fromisoformat(d_str),
            ).first()
            if exist:
                if not exist.order_id and order_id:
                    exist.order_id = order_id
                continue
            s = ConsultantSchedule(
                consultant_id=assistant_id,
                schedule_date=date.fromisoformat(d_str),
                city=body.get('city', ''),
                schedule_type=stype,
                title=body.get('title', ''),
                remark=body.get('remark', '') + '（助理）',
                order_id=order_id,
                created_by=current.user_id,
            )
            db.add(s)
            asst_created.append(d_str)

    db.commit()
    result = {'created': len(created), 'dates': created}
    if auto_order:
        result['auto_order_id'] = auto_order.id
        result['auto_order_no'] = auto_order.order_no
    if asst_created:
        result['assistant_created'] = len(asst_created)
    return ok(result)


@router.put("/schedules/{sid}")
def update_schedule(
    sid: int,
    body: dict,
    db: Session = Depends(get_db),
    current = Depends(get_current_admin_or_consultant),
):
    s = db.query(ConsultantSchedule).filter(ConsultantSchedule.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="排期不存在")
    if current.is_consultant and s.consultant_id != current.consultant_id:
        raise HTTPException(status_code=403, detail="只能修改自己的排期")
    for k in ['city', 'schedule_type', 'title', 'remark']:
        if k in body:
            setattr(s, k, body[k])
    db.commit()
    db.refresh(s)
    return ok(to_dict(s))


@router.delete("/schedules/{sid}")
def delete_schedule(
    sid: int,
    db: Session = Depends(get_db),
    current = Depends(get_current_admin_or_consultant),
):
    s = db.query(ConsultantSchedule).filter(ConsultantSchedule.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="排期不存在")
    if current.is_consultant and s.consultant_id != current.consultant_id:
        raise HTTPException(status_code=403, detail="只能删除自己的排期")
    db.delete(s)
    db.commit()
    return ok({'msg': '已删除'})


# ---------- 看板 ----------
def list_operation_logs(
    page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current: AdminUser = Depends(require_super_admin),
):
    result = db.execute(text("""
        SELECT * FROM operation_logs ORDER BY created_at DESC
        LIMIT :size OFFSET :offset
    """), {'size': size, 'offset': (page-1)*size}).fetchall()
    total = db.execute(text("SELECT COUNT(*) FROM operation_logs")).scalar()
    return ok({
        'total': total, 'page': page, 'size': size,
        'items': [dict(r._mapping) for r in result]
    })


# ---------- 看板 ----------
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db),
              _: AdminUser = Depends(get_admin_or_agent)):
    today = date.today()
    y, mo = today.year, today.month

    total_members = db.query(func.count(Member.id)).scalar() or 0
    new_this_month = (
        db.query(func.count(Member.id))
        .filter(extract("year", Member.created_at) == y,
                extract("month", Member.created_at) == mo)
        .scalar() or 0
    )
    trial = db.query(func.count(Member.id)).filter(Member.member_type == "trial").scalar() or 0
    annual = db.query(func.count(Member.id)).filter(Member.member_type == "annual").scalar() or 0
    trial_conv = round(annual / (trial + annual) * 100, 1) if (trial + annual) else 0.0

    year_income = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.pay_status.in_(["paid", "partial"]),
                extract("year", Payment.pay_time) == y)
        .scalar() or 0
    )
    month_income = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.pay_status.in_(["paid", "partial"]),
                extract("year", Payment.pay_time) == y,
                extract("month", Payment.pay_time) == mo)
        .scalar() or 0
    )
    # 年度欠款合计
    year_debt = (
        db.query(func.coalesce(func.sum(Payment.debt_amount), 0))
        .filter(Payment.pay_status == "partial",
                extract("year", Payment.pay_time) == y)
        .scalar() or 0
    )

    total_refer = db.query(func.count(Referral.id)).scalar() or 0
    confirmed_refer = db.query(func.count(Referral.id)).filter(Referral.status == "confirmed").scalar() or 0
    refer_conv = round(confirmed_refer / total_refer * 100, 1) if total_refer else 0.0

    # 下店统计：一个客户(member_id) = 一家店，天数按排期天数累加
    from sqlalchemy import distinct
    # 专案工单：按 member_id 去重 = 家数，天数从排期表按 order_id 关联的记录数
    order_stores = (
        db.query(func.count(distinct(ServiceOrder.member_id)))
        .filter(ServiceOrder.status.notin_(["cancelled", "pending"]),
                extract("year", ServiceOrder.appoint_date) == y,
                extract("month", ServiceOrder.appoint_date) == mo)
        .scalar() or 0
    )
    order_days = (
        db.query(func.count(ConsultantSchedule.id))
        .filter(ConsultantSchedule.schedule_type == "busy",
                ConsultantSchedule.order_id.isnot(None),
                extract("year", ConsultantSchedule.schedule_date) == y,
                extract("month", ConsultantSchedule.schedule_date) == mo)
        .scalar() or 0
    )
    # 下店预约表：按 member_id 去重 = 家数
    booking_stores = (
        db.query(func.count(distinct(VisitBooking.member_id)))
        .filter(VisitBooking.status.in_(["confirmed", "completed"]),
                extract("year", VisitBooking.confirmed_date) == y,
                extract("month", VisitBooking.confirmed_date) == mo)
        .scalar() or 0
    )
    booking_days = (
        db.query(func.count(VisitBooking.id))
        .filter(VisitBooking.status.in_(["confirmed", "completed"]),
                extract("year", VisitBooking.confirmed_date) == y,
                extract("month", VisitBooking.confirmed_date) == mo)
        .scalar() or 0
    )
    # 手动排期（无order_id关联的）按 title 去重
    manual_stores = (
        db.query(func.count(distinct(ConsultantSchedule.title)))
        .filter(ConsultantSchedule.schedule_type == "busy",
                ConsultantSchedule.order_id.is_(None),
                ConsultantSchedule.title.isnot(None),
                ConsultantSchedule.title != "",
                extract("year", ConsultantSchedule.schedule_date) == y,
                extract("month", ConsultantSchedule.schedule_date) == mo)
        .scalar() or 0
    )
    manual_days = (
        db.query(func.count(ConsultantSchedule.id))
        .filter(ConsultantSchedule.schedule_type == "busy",
                ConsultantSchedule.order_id.is_(None),
                extract("year", ConsultantSchedule.schedule_date) == y,
                extract("month", ConsultantSchedule.schedule_date) == mo)
        .scalar() or 0
    )
    month_visit = order_stores + booking_stores + manual_stores   # 家数（去重）
    month_visit_days = order_days + booking_days + manual_days    # 总天数
    reward_pending = db.query(func.count(VisitReward.id)).filter(VisitReward.status == "available").scalar() or 0

    return ok({
        "total_members": int(total_members),
        "new_this_month": int(new_this_month),
        "trial_conv": trial_conv,
        "year_income": float(year_income),
        "month_income": float(month_income),
        "year_debt": float(year_debt),
        "refer_conv": refer_conv,
        "month_visit": int(month_visit),
        "month_visit_days": int(month_visit_days),
        "reward_pending": int(reward_pending),
    })



# ──────────────────── 数据看板 V2（完整版） ────────────────────

@router.get("/dashboard/v2")
def dashboard_v2(
    year: int = None,
    month: int = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    """CRM 完整数据看板
    四大模块：会员/学员 · 老师 · 财务 · 数据分析
    """
    from sqlalchemy import distinct, case, literal_column
    from models.branch import Branch

    today = date.today()
    y = year or today.year
    mo = month or today.month

    # ═══════════ 一、会员/学员 ═══════════

    # 本月服务店家数（按 member_id 去重）
    month_service_stores = (
        db.query(func.count(distinct(ServiceOrder.member_id)))
        .filter(ServiceOrder.status.notin_(["cancelled", "pending"]),
                extract("year", ServiceOrder.appoint_date) == y,
                extract("month", ServiceOrder.appoint_date) == mo)
        .scalar() or 0
    )

    # 服务天数
    month_service_days = (
        db.query(func.count(ConsultantSchedule.id))
        .filter(ConsultantSchedule.schedule_type == "busy",
                extract("year", ConsultantSchedule.schedule_date) == y,
                extract("month", ConsultantSchedule.schedule_date) == mo)
        .scalar() or 0
    )

    # 客户推荐数
    month_referrals = (
        db.query(func.count(Referral.id))
        .filter(extract("year", Referral.created_at) == y,
                extract("month", Referral.created_at) == mo)
        .scalar() or 0
    )

    # 课程参加人数
    month_course_attendees = (
        db.query(func.count(CourseEnrollment.id))
        .filter(CourseEnrollment.status.in_(["enrolled", "checked_in", "completed"]),
                extract("year", CourseEnrollment.created_at) == y,
                extract("month", CourseEnrollment.created_at) == mo)
        .scalar() or 0
    )

    # 权益升级店数（本月 member_tier 发生升级的 member 数 — 用 annual_spending 变化近似）
    month_tier_upgrades = (
        db.query(func.count(distinct(Member.id)))
        .filter(Member.member_type == "annual",
                extract("year", Member.updated_at) == y,
                extract("month", Member.updated_at) == mo)
        .scalar() or 0
    )

    # ═══════════ 二、老师 ═══════════

    # 本月出差老师人数
    month_active_consultants = (
        db.query(func.count(distinct(ConsultantSchedule.consultant_id)))
        .filter(ConsultantSchedule.schedule_type == "busy",
                extract("year", ConsultantSchedule.schedule_date) == y,
                extract("month", ConsultantSchedule.schedule_date) == mo)
        .scalar() or 0
    )

    # 老师服务店家数（去重 title/member）
    consultant_service_stores = (
        db.query(func.count(distinct(ServiceOrder.member_id)))
        .filter(ServiceOrder.consultant_id.isnot(None),
                ServiceOrder.status.notin_(["cancelled", "pending"]),
                extract("year", ServiceOrder.appoint_date) == y,
                extract("month", ServiceOrder.appoint_date) == mo)
        .scalar() or 0
    )

    # 老师出差天数
    consultant_travel_days = month_service_days  # 同排期表

    # 老师销售金额
    consultant_sales = float(
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.pay_status.in_(["paid", "partial"]),
                Payment.consultant_id.isnot(None),
                extract("year", Payment.pay_time) == y,
                extract("month", Payment.pay_time) == mo)
        .scalar() or 0
    )

    # 消耗金额（已完成服务的扣费 = 已完成工单对应的 service price / total_times）
    from sqlalchemy.orm import aliased
    SvcAlias = aliased(Service)
    consumed_amount = float(
        db.query(func.coalesce(func.sum(
            case(
                (SvcAlias.total_times > 0, SvcAlias.price / SvcAlias.total_times),
                else_=0
            )
        ), 0))
        .select_from(ServiceOrder)
        .join(SvcAlias, ServiceOrder.service_id == SvcAlias.id)
        .filter(ServiceOrder.status.in_(["completed", "in_progress", "follow_up"]),
                extract("year", ServiceOrder.appoint_date) == y,
                extract("month", ServiceOrder.appoint_date) == mo)
        .scalar() or 0
    )

    # 休息天数（schedule_type=off 或 该月总天数 - busy天数）
    import calendar as cal_mod
    days_in_month = cal_mod.monthrange(y, mo)[1]
    # Consultant already imported from models
    active_consultants = db.query(Consultant).filter(Consultant.status == "active").all()
    total_consultant_days = len(active_consultants) * days_in_month
    rest_days = total_consultant_days - month_service_days

    # 老师归属客户数（consultant_id 关联的 members）
    total_assigned_members = int(
        db.query(func.count(Member.id))
        .filter(Member.consultant_id.isnot(None), Member.status == "active")
        .scalar() or 0
    )

    # 老师跟进客户数（本月 follow_ups 去重 member_id）
    from models.followup import FollowUp
    total_followed_members = int(
        db.query(func.count(distinct(FollowUp.member_id)))
        .filter(extract("year", FollowUp.created_at) == y,
                extract("month", FollowUp.created_at) == mo)
        .scalar() or 0
    )

    # ═══════════ 三、财务数据 ═══════════

    branches = db.query(Branch).filter(Branch.status == "active").all()
    branch_data = []
    total_sales = 0
    total_consumed = 0
    total_debt = 0
    total_branch_stores = 0
    total_branch_days = 0

    for b in branches:
        # 分公司关联的老师（用branch_id）
        branch_consultants = (
            db.query(Consultant.id)
            .filter(Consultant.branch_id == b.id, Consultant.status == "active")
            .all()
        )
        c_ids = [c.id for c in branch_consultants]

        b_sales = 0
        b_consumed = 0
        b_debt = 0
        b_stores = 0
        b_days = 0

        if c_ids:
            b_sales = float(
                db.query(func.coalesce(func.sum(Payment.amount), 0))
                .filter(Payment.consultant_id.in_(c_ids),
                        Payment.pay_status.in_(["paid", "partial"]),
                        extract("year", Payment.pay_time) == y,
                        extract("month", Payment.pay_time) == mo)
                .scalar() or 0
            )
            b_debt = float(
                db.query(func.coalesce(func.sum(Payment.debt_amount), 0))
                .filter(Payment.consultant_id.in_(c_ids),
                        Payment.pay_status == "partial",
                        extract("year", Payment.pay_time) == y)
                .scalar() or 0
            )
            b_stores = int(
                db.query(func.count(distinct(ServiceOrder.member_id)))
                .filter(ServiceOrder.consultant_id.in_(c_ids),
                        ServiceOrder.status.notin_(["cancelled", "pending"]),
                        extract("year", ServiceOrder.appoint_date) == y,
                        extract("month", ServiceOrder.appoint_date) == mo)
                .scalar() or 0
            )
            b_days = int(
                db.query(func.count(ConsultantSchedule.id))
                .filter(ConsultantSchedule.consultant_id.in_(c_ids),
                        ConsultantSchedule.schedule_type == "busy",
                        extract("year", ConsultantSchedule.schedule_date) == y,
                        extract("month", ConsultantSchedule.schedule_date) == mo)
                .scalar() or 0
            )
            b_consumed = float(
                db.query(func.coalesce(func.sum(
                    case(
                        (SvcAlias.total_times > 0, SvcAlias.price / SvcAlias.total_times),
                        else_=0
                    )
                ), 0))
                .select_from(ServiceOrder)
                .join(SvcAlias, ServiceOrder.service_id == SvcAlias.id)
                .filter(ServiceOrder.consultant_id.in_(c_ids),
                        ServiceOrder.status.in_(["completed", "in_progress", "follow_up"]),
                        extract("year", ServiceOrder.appoint_date) == y,
                        extract("month", ServiceOrder.appoint_date) == mo)
                .scalar() or 0
            )

        total_sales += b_sales
        total_consumed += b_consumed
        total_debt += b_debt
        total_branch_stores += b_stores
        total_branch_days += b_days

        b_consultant_count = len(c_ids)
        branch_data.append({
            "id": b.id,
            "name": b.name,
            "short_name": b.short_name or b.name,
            "city": b.city or "",
            "consultant_count": b_consultant_count,
            "sales": b_sales,
            "consumed": b_consumed,
            "debt": b_debt,
            "stores": b_stores,
            "travel_days": b_days,
        })

    # ═══════════ 四、数据分析 ═══════════

    # 试听转化率
    total_trial = db.query(func.count(Member.id)).filter(Member.member_type == "trial").scalar() or 0
    total_annual = db.query(func.count(Member.id)).filter(Member.member_type == "annual").scalar() or 0
    trial_conv = round(total_annual / (total_trial + total_annual) * 100, 1) if (total_trial + total_annual) else 0

    # 推荐转化率
    total_ref = db.query(func.count(Referral.id)).scalar() or 0
    confirmed_ref = db.query(func.count(Referral.id)).filter(Referral.status == "confirmed").scalar() or 0
    referral_conv = round(confirmed_ref / total_ref * 100, 1) if total_ref else 0

    # 客户推荐排名 TOP10
    referral_rank = (
        db.query(Member.name, func.count(Referral.id).label("cnt"))
        .join(Referral, Referral.referrer_id == Member.id)
        .group_by(Member.id, Member.name)
        .order_by(func.count(Referral.id).desc())
        .limit(10)
        .all()
    )

    # 老师出差天数排名
    consultant_days_rank = (
        db.query(Consultant.name,
                 func.count(ConsultantSchedule.id).label("days"))
        .join(ConsultantSchedule, ConsultantSchedule.consultant_id == Consultant.id)
        .filter(ConsultantSchedule.schedule_type == "busy",
                extract("year", ConsultantSchedule.schedule_date) == y,
                extract("month", ConsultantSchedule.schedule_date) == mo)
        .group_by(Consultant.id, Consultant.name)
        .order_by(func.count(ConsultantSchedule.id).desc())
        .all()
    )

    # 老师服务案例数排名
    consultant_cases_rank = (
        db.query(Consultant.name,
                 func.count(ServiceOrder.id).label("cases"))
        .join(ServiceOrder, ServiceOrder.consultant_id == Consultant.id)
        .filter(ServiceOrder.status.notin_(["cancelled", "pending"]),
                extract("year", ServiceOrder.appoint_date) == y,
                extract("month", ServiceOrder.appoint_date) == mo)
        .group_by(Consultant.id, Consultant.name)
        .order_by(func.count(ServiceOrder.id).desc())
        .all()
    )

    # 老师销售排名
    consultant_sales_rank = (
        db.query(Consultant.name,
                 func.coalesce(func.sum(Payment.amount), 0).label("sales"))
        .join(Payment, Payment.consultant_id == Consultant.id)
        .filter(Payment.pay_status.in_(["paid", "partial"]),
                extract("year", Payment.pay_time) == y,
                extract("month", Payment.pay_time) == mo)
        .group_by(Consultant.id, Consultant.name)
        .order_by(func.coalesce(func.sum(Payment.amount), 0).desc())
        .all()
    )

    # 老师消耗排名
    consultant_consumed_rank = (
        db.query(Consultant.name,
                 func.count(ServiceOrder.id).label("consumed_count"))
        .join(ServiceOrder, ServiceOrder.consultant_id == Consultant.id)
        .filter(ServiceOrder.status.in_(["completed", "in_progress", "follow_up"]),
                extract("year", ServiceOrder.appoint_date) == y,
                extract("month", ServiceOrder.appoint_date) == mo)
        .group_by(Consultant.id, Consultant.name)
        .order_by(func.count(ServiceOrder.id).desc())
        .all()
    )

    # 老师归属客户排名
    consultant_assigned_rank = (
        db.query(Consultant.name,
                 func.count(Member.id).label("cnt"))
        .join(Member, Member.consultant_id == Consultant.id)
        .filter(Member.status == "active")
        .group_by(Consultant.id, Consultant.name)
        .order_by(func.count(Member.id).desc())
        .all()
    )

    # 老师跟进客户排名（本月）
    consultant_followed_rank_raw = (
        db.query(FollowUp.admin_name,
                 func.count(distinct(FollowUp.member_id)).label("cnt"))
        .filter(extract("year", FollowUp.created_at) == y,
                extract("month", FollowUp.created_at) == mo)
        .group_by(FollowUp.admin_name)
        .order_by(func.count(distinct(FollowUp.member_id)).desc())
        .all()
    )

    # 老师成交率：归属客户中有付款记录的比例
    consultant_conversion = []
    for c in active_consultants:
        assigned = db.query(func.count(Member.id)).filter(
            Member.consultant_id == c.id, Member.status == "active"
        ).scalar() or 0
        if assigned == 0:
            continue
        paid = db.query(func.count(distinct(Payment.member_id))).filter(
            Payment.consultant_id == c.id,
            Payment.pay_status.in_(["paid", "partial"])
        ).scalar() or 0
        rate = round(paid / assigned * 100, 1) if assigned else 0
        consultant_conversion.append({
            "name": c.name,
            "assigned": assigned,
            "paid": paid,
            "rate": rate,
        })
    consultant_conversion.sort(key=lambda x: x["rate"], reverse=True)

    # 分公司排名（按销售额）
    branch_rank = sorted(branch_data, key=lambda x: x["sales"], reverse=True)

    return ok({
        "year": y,
        "month": mo,
        "member": {
            "month_service_stores": int(month_service_stores),
            "month_service_days": int(month_service_days),
            "month_referrals": int(month_referrals),
            "month_course_attendees": int(month_course_attendees),
            "month_tier_upgrades": int(month_tier_upgrades),
        },
        "consultant": {
            "active_count": int(month_active_consultants),
            "service_stores": int(consultant_service_stores),
            "travel_days": int(consultant_travel_days),
            "sales": consultant_sales,
            "consumed": consumed_amount,
            "rest_days": max(0, rest_days),
            "assigned_members": total_assigned_members,
            "followed_members": total_followed_members,
        },
        "finance": {
            "total_sales": total_sales,
            "total_consumed": total_consumed,
            "total_debt": total_debt,
            "total_stores": total_branch_stores,
            "total_travel_days": total_branch_days,
            "branches": branch_data,
        },
        "analysis": {
            "trial_conv": trial_conv,
            "referral_conv": referral_conv,
            "referral_rank": [{"name": r[0], "count": r[1]} for r in referral_rank],
            "consultant_days_rank": [{"name": r[0], "days": r[1]} for r in consultant_days_rank],
            "consultant_cases_rank": [{"name": r[0], "cases": r[1]} for r in consultant_cases_rank],
            "consultant_sales_rank": [{"name": r[0], "sales": float(r[1])} for r in consultant_sales_rank],
            "consultant_consumed_rank": [{"name": r[0], "count": r[1]} for r in consultant_consumed_rank],
            "branch_rank": branch_rank,
            "consultant_assigned_rank": [{"name": r[0], "count": r[1]} for r in consultant_assigned_rank],
            "consultant_followed_rank": [{"name": r[0] or "", "count": r[1]} for r in consultant_followed_rank_raw],
            "consultant_conversion": consultant_conversion,
        },
    })


# ──────────────────── 经营驾驶舱（今日待办 + 跟进提醒） ────────────────────

def _iso_dt(value):
    return value.isoformat() if value else None


def _iso_date(value):
    return value.isoformat() if value else None


def _safe_float(value) -> float:
    return float(value or 0)


def _todo(category: str, title: str, subtitle: str, ref_type: str, ref_id: int,
          action_url: str, priority: str = "normal", due_at=None, assignee=None, meta=None):
    return {
        "id": f"{category}:{ref_id}",
        "category": category,
        "priority": priority,
        "title": title,
        "subtitle": subtitle,
        "due_at": _iso_dt(due_at) if isinstance(due_at, datetime) else _iso_date(due_at),
        "assignee": assignee,
        "ref": {"type": ref_type, "id": ref_id},
        "action_url": action_url,
        "meta": meta or {},
    }


@router.get("/dashboard/cockpit")
def dashboard_cockpit(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD，默认今天"),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    """经营驾驶舱：今日 KPI、待办任务、客户跟进提醒。"""
    try:
        day = date.fromisoformat(target_date) if target_date else date.today()
    except Exception:
        raise HTTPException(status_code=400, detail="target_date 格式应为 YYYY-MM-DD")

    day_start = datetime.combine(day, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    month_start = day.replace(day=1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    paid_statuses = ["paid", "partial"]
    payment_time = func.coalesce(Payment.pay_time, Payment.created_at)

    today_payment_amount = _safe_float(
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.pay_status.in_(paid_statuses), payment_time >= day_start, payment_time < day_end)
        .scalar()
    )
    today_payment_count = int(
        db.query(func.count(Payment.id))
        .filter(Payment.pay_status.in_(paid_statuses), payment_time >= day_start, payment_time < day_end)
        .scalar() or 0
    )
    today_new_members = int(
        db.query(func.count(Member.id))
        .filter(Member.created_at >= day_start, Member.created_at < day_end)
        .scalar() or 0
    )
    today_service_orders = int(
        db.query(func.count(ServiceOrder.id))
        .filter(ServiceOrder.appoint_date == day, ServiceOrder.status != "cancelled")
        .scalar() or 0
    )
    today_bookings = int(
        db.query(func.count(VisitBooking.id))
        .filter(VisitBooking.confirmed_date == day, VisitBooking.status.in_(["confirmed", "in_progress"]))
        .scalar() or 0
    )
    today_course_sessions = 0
    try:
        from models.course_session import CourseSession as CourseSessionV2
        today_course_sessions = int(
            db.query(func.count(CourseSessionV2.id))
            .filter(CourseSessionV2.start_date <= day, CourseSessionV2.end_date >= day,
                    CourseSessionV2.status.in_(["enrolling", "ongoing"]))
            .scalar() or 0
        )
    except Exception:
        today_course_sessions = 0

    month_payment_amount = _safe_float(
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.pay_status.in_(paid_statuses),
                payment_time >= datetime.combine(month_start, datetime.min.time()),
                payment_time < datetime.combine(next_month, datetime.min.time()))
        .scalar()
    )
    month_debt_amount = _safe_float(
        db.query(func.coalesce(func.sum(Payment.debt_amount), 0))
        .filter(Payment.debt_amount > 0, Payment.pay_status.in_(["pending", "partial"]))
        .scalar()
    )
    month_service_stores = int(
        db.query(func.count(func.distinct(ServiceOrder.member_id)))
        .filter(ServiceOrder.status.notin_(["cancelled", "pending"]),
                ServiceOrder.appoint_date >= month_start,
                ServiceOrder.appoint_date < next_month)
        .scalar() or 0
    )

    todos = []
    # 新预约待确认
    pending_bookings = (
        db.query(VisitBooking)
        .filter(VisitBooking.status == "pending")
        .order_by(VisitBooking.apply_time.asc())
        .limit(8)
        .all()
    )
    for b in pending_bookings:
        member = db.query(Member).filter(Member.id == b.member_id).first() if b.member_id else None
        todos.append(_todo(
            "booking",
            f"预约待确认 · {member.name if member else '未知客户'}",
            f"{b.city or ''} {b.preferred_date or ''}".strip() or "客户提交了下店预约",
            "visit_booking",
            b.id,
            "/bookings",
            "high",
            b.preferred_date,
            meta={"member_id": b.member_id},
        ))

    # 服务工单待处理
    pending_orders = (
        db.query(ServiceOrder)
        .filter(ServiceOrder.status.in_(["pending", "confirmed"]))
        .order_by(ServiceOrder.created_at.asc())
        .limit(8)
        .all()
    )
    for o in pending_orders:
        member = db.query(Member).filter(Member.id == o.member_id).first() if o.member_id else None
        consultant = db.query(Consultant).filter(Consultant.id == o.consultant_id).first() if o.consultant_id else None
        todos.append(_todo(
            "service_order",
            f"工单待处理 · {o.order_no or ('#' + str(o.id))}",
            f"{member.name if member else '未关联客户'} · {o.workflow_stage or o.status}",
            "service_order",
            o.id,
            f"/service-orders/{o.id}",
            "high" if o.status == "pending" else "normal",
            o.appoint_date,
            {"id": consultant.id, "name": consultant.name, "type": "consultant"} if consultant else None,
            {"member_id": o.member_id},
        ))

    # 欠款/补款到期
    due_payments = (
        db.query(Payment)
        .filter(Payment.debt_amount > 0,
                Payment.pay_status.in_(["pending", "partial"]),
                Payment.due_date.isnot(None),
                Payment.due_date <= day + timedelta(days=1))
        .order_by(Payment.due_date.asc())
        .limit(8)
        .all()
    )
    for p in due_payments:
        member = db.query(Member).filter(Member.id == p.member_id).first() if p.member_id else None
        priority = "high" if p.due_date and p.due_date <= day else "normal"
        todos.append(_todo(
            "payment_due",
            f"补款提醒 · {member.name if member else '未知客户'}",
            f"待补 {p.debt_amount or 0} 元，截止 {p.due_date or '未设置'}",
            "payment",
            p.id,
            f"/members/{p.member_id}" if p.member_id else "/payments",
            priority,
            p.due_date,
            meta={"member_id": p.member_id, "debt_amount": _safe_float(p.debt_amount)},
        ))

    # 老师申请待审核
    pending_approvals = (
        db.query(AdminUser)
        .filter(AdminUser.role == "pending")
        .order_by(AdminUser.created_at.asc())
        .limit(5)
        .all()
    )
    for a in pending_approvals:
        todos.append(_todo(
            "consultant_approval",
            f"老师账号待审核 · {a.real_name or a.username}",
            a.phone or "请尽快完成审核",
            "admin_user",
            a.id,
            "/consultant-approval",
            "normal",
            a.created_at,
        ))

    followup_reminders = []
    # 会员 CRM 跟进提醒
    try:
        from models.followup import FollowUp
        followups = (
            db.query(FollowUp)
            .filter(FollowUp.next_follow_date.isnot(None),
                    FollowUp.next_follow_date < day_end,
                    FollowUp.status.notin_(["closed", "lost"]))
            .order_by(FollowUp.next_follow_date.asc())
            .limit(20)
            .all()
        )
        for f in followups:
            member = db.query(Member).filter(Member.id == f.member_id).first()
            consultant = db.query(Consultant).filter(Consultant.id == member.consultant_id).first() if member and member.consultant_id else None
            overdue_days = max(0, (day - f.next_follow_date.date()).days) if f.next_follow_date else 0
            followup_reminders.append({
                "source": "member_followup",
                "source_label": "客户跟进",
                "member_id": f.member_id,
                "member_name": member.name if member else "",
                "enterprise_name": member.enterprise_name if member else "",
                "consultant_id": consultant.id if consultant else None,
                "consultant_name": consultant.name if consultant else "",
                "next_follow_at": _iso_dt(f.next_follow_date),
                "overdue_days": overdue_days,
                "last_follow_at": _iso_dt(f.created_at),
                "followup_count": 1,
                "status_label": {"intention": "意向客户", "following": "跟进中", "silent": "沉默客户"}.get(f.status, f.status),
                "ref": {"type": "follow_up", "id": f.id},
                "action_url": f"/members/{f.member_id}",
            })
    except Exception:
        pass

    # 课程课后跟进提醒
    try:
        from models.course_session import CourseEnrollment as CourseEnrollmentV2, CourseSession as CourseSessionV2
        course_followups = (
            db.query(CourseEnrollmentV2)
            .filter(CourseEnrollmentV2.signed_deal == False,
                    CourseEnrollmentV2.status == "follow_up",
                    CourseEnrollmentV2.next_followup_date.isnot(None),
                    CourseEnrollmentV2.next_followup_date <= day)
            .order_by(CourseEnrollmentV2.next_followup_date.asc())
            .limit(15)
            .all()
        )
        for e in course_followups:
            member = db.query(Member).filter(Member.id == e.member_id).first()
            consultant = db.query(Consultant).filter(Consultant.id == e.consultant_id).first() if e.consultant_id else None
            session_obj = db.query(CourseSessionV2).filter(CourseSessionV2.id == e.session_id).first()
            followup_reminders.append({
                "source": "course_enrollment",
                "source_label": "课后跟进",
                "member_id": e.member_id,
                "member_name": member.name if member else "",
                "enterprise_name": member.enterprise_name if member else "",
                "consultant_id": e.consultant_id,
                "consultant_name": consultant.name if consultant else "",
                "next_follow_at": _iso_date(e.next_followup_date),
                "overdue_days": max(0, (day - e.next_followup_date).days) if e.next_followup_date else 0,
                "last_follow_at": _iso_dt(e.last_followup_at),
                "followup_count": e.followup_count or 0,
                "status_label": session_obj.title if session_obj else "课后跟进",
                "ref": {"type": "course_enrollment", "id": e.id},
                "action_url": f"/course-sessions",
            })
    except Exception:
        pass

    # 工单回访阶段提醒
    followup_orders = (
        db.query(ServiceOrder)
        .filter(ServiceOrder.status == "follow_up")
        .order_by(ServiceOrder.updated_at.asc())
        .limit(10)
        .all()
    )
    for o in followup_orders:
        member = db.query(Member).filter(Member.id == o.member_id).first() if o.member_id else None
        consultant = db.query(Consultant).filter(Consultant.id == o.consultant_id).first() if o.consultant_id else None
        ref_day = o.updated_at.date() if o.updated_at else day
        followup_reminders.append({
            "source": "service_order",
            "source_label": "工单回访",
            "member_id": o.member_id,
            "member_name": member.name if member else "",
            "enterprise_name": member.enterprise_name if member else "",
            "consultant_id": o.consultant_id,
            "consultant_name": consultant.name if consultant else "",
            "next_follow_at": _iso_dt(o.updated_at) or _iso_date(o.appoint_date),
            "overdue_days": max(0, (day - ref_day).days),
            "last_follow_at": _iso_dt(o.updated_at),
            "followup_count": 0,
            "status_label": o.workflow_stage or "跟进回访",
            "ref": {"type": "service_order", "id": o.id},
            "action_url": f"/service-orders/{o.id}",
        })

    followup_reminders.sort(key=lambda x: (x.get("overdue_days", 0), x.get("next_follow_at") or ""), reverse=True)
    followup_reminders = followup_reminders[:30]

    due_today_count = sum(1 for t in todos if t["category"] == "payment_due" and t["priority"] == "high")
    followup_overdue = sum(1 for f in followup_reminders if f.get("overdue_days", 0) > 0)
    followup_due_today = sum(1 for f in followup_reminders if f.get("overdue_days", 0) == 0)

    return ok({
        "date": day.isoformat(),
        "kpi": {
            "today": {
                "payment_amount": today_payment_amount,
                "payment_count": today_payment_count,
                "new_members": today_new_members,
                "service_orders_today": today_service_orders,
                "bookings_today": today_bookings,
                "course_sessions_today": today_course_sessions,
            },
            "month": {
                "payment_amount": month_payment_amount,
                "debt_amount": month_debt_amount,
                "service_stores": month_service_stores,
            },
        },
        "todos": todos[:30],
        "followup_reminders": followup_reminders,
        "summary": {
            "todo_total": len(todos),
            "followup_total": len(followup_reminders),
            "followup_overdue": followup_overdue,
            "followup_due_today": followup_due_today,
            "payment_due_today": due_today_count,
        },
    })


# ──────────────────── 菜单徽标 ────────────────────

@router.get("/stats/menu-badges")
def menu_badges(db: Session = Depends(get_db),
                _: AdminUser = Depends(get_admin_or_agent)):
    """返回侧栏菜单徽标数字"""
    from models.service import ServiceOrder
    from models.course_session import CourseSession
    import datetime

    # 预约管理 - 仅 pending（未确认的新预约）
    pending_bookings = (
        db.query(func.count(VisitBooking.id))
        .filter(VisitBooking.status == "pending")
        .scalar() or 0
    )
    # 权益台账 - 可用
    pending_rewards = (
        db.query(func.count(VisitReward.id))
        .filter(VisitReward.status == "available")
        .scalar() or 0
    )
    # 服务工单 - 待接单（红）
    try:
        pending_orders = (
            db.query(func.count(ServiceOrder.id))
            .filter(ServiceOrder.status.in_(["pending", "confirmed"]))
            .scalar() or 0
        )
    except:
        pending_orders = 0
    # 服务工单 - 进行中（绿）
    try:
        active_orders = (
            db.query(func.count(ServiceOrder.id))
            .filter(ServiceOrder.status.in_(["accepted", "in_progress", "preparing", "reporting", "follow_up"]))
            .scalar() or 0
        )
    except:
        active_orders = 0
    # 课程场次 - 待确认报名（红）
    try:
        pending_sessions = (
            db.query(func.count(CourseSession.id))
            .filter(CourseSession.status == "open")
            .scalar() or 0
        )
    except:
        pending_sessions = 0
    # 老师排期 - 进行中/已确认
    try:
        active_schedules = (
            db.query(func.count(VisitBooking.id))
            .filter(VisitBooking.status.in_(["confirmed", "in_progress"]))
            .scalar() or 0
        )
    except:
        active_schedules = 0
    # 会员 - 不显示角标（信息类，非待办）
    new_members = 0
    # 权益台账 - 待确认发放的（非已激活）
    try:
        pending_rewards_action = (
            db.query(func.count(VisitReward.id))
            .filter(VisitReward.status == "pending")
            .scalar() or 0
        )
    except:
        pending_rewards_action = 0
    # 老师审核 - 待审核
    try:
        pending_approval = (
            db.query(func.count(AdminUser.id))
            .filter(AdminUser.role == "pending")
            .scalar() or 0
        )
    except:
        pending_approval = 0
    return ok({
        "bookings": int(pending_bookings),
        "rewards": int(pending_rewards_action),
        "service-orders": int(pending_orders),
        "service-orders-active": int(active_orders),
        "course-sessions": int(pending_sessions),
        "schedules": 0,
        "schedules-active": int(active_schedules),
        "members": int(new_members),
        "consultant-approval": int(pending_approval),
    })


# ──────────────────── 统一注册 ────────────────────

class UserRegisterIn(BaseModel):
    name: str
    phone: str
    password: str
    company: Optional[str] = None


@router.post("/register")
def user_register(body: UserRegisterIn, db: Session = Depends(get_db)):
    """所有人统一注册入口（管理员/老师均可）→ 默认 pending，等超管分配角色"""
    import bcrypt
    exist = db.query(AdminUser).filter(AdminUser.phone == body.phone).first()
    if exist:
        raise HTTPException(400, "该手机号已注册")
    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    new_user = AdminUser(
        username=body.phone,
        password_hash=pw_hash,
        real_name=body.name,
        phone=body.phone,
        company=body.company,
        role="pending",
        status="pending",
    )
    db.add(new_user)
    db.commit()

    # 通知所有超管
    try:
        from routers.notifications import push_notification
        supers = db.query(AdminUser).filter(
            AdminUser.role == "super_admin", AdminUser.status == "active"
        ).all()
        for s in supers:
            push_notification(
                db, "admin", s.id,
                title=f"新用户注册 · {body.name}",
                body=f"{body.name}（{body.phone}）已注册，请到「账号管理」分配角色",
                ntype="application",
            )
        db.commit()
    except Exception:
        pass

    return ok({"msg": "注册成功，请等待管理员分配权限后登录"})


# ──────────────────── 账号管理（超管专用）────────────────────

@router.get("/users")
def list_users(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current=Depends(require_super_admin),
):
    """获取所有用户列表"""
    q = db.query(AdminUser)
    if status:
        q = q.filter(AdminUser.status == status)
    users = q.order_by(AdminUser.created_at.desc()).all()
    return ok([{
        "id": u.id, "username": u.username, "real_name": u.real_name,
        "phone": u.phone, "company": u.company,
        "role": u.role, "status": u.status,
        "created_at": str(u.created_at)[:16] if u.created_at else "",
    } for u in users])


class AssignRoleIn(BaseModel):
    role: str       # super_admin / admin / consultant
    company: Optional[str] = None


@router.post("/users/{uid}/assign-role")
def assign_role(
    uid: int,
    body: AssignRoleIn,
    db: Session = Depends(get_db),
    current=Depends(require_super_admin),
):
    """超管分配角色并激活账号"""
    valid_roles = ["super_admin", "admin", "consultant"]
    if body.role not in valid_roles:
        raise HTTPException(400, f"角色必须是: {', '.join(valid_roles)}")

    u = db.query(AdminUser).filter(AdminUser.id == uid).first()
    if not u:
        raise HTTPException(404, "用户不存在")

    old_role = u.role
    u.role = body.role
    u.status = "active"
    if body.company:
        u.company = body.company

    log_operation(db, current, "assign_role", "admin_user", uid,
                  f"{u.real_name} 角色从 {old_role} → {body.role}")
    db.commit()

    # 如果是老师角色，同步创建 consultant 记录
    if body.role == "consultant":
        from models.booking import Consultant
        exist_c = db.query(Consultant).filter(Consultant.phone == u.phone).first()
        if not exist_c:
            import hashlib
            c = Consultant(
                name=u.real_name,
                phone=u.phone,
                company=u.company or body.company,
                password_hash=u.password_hash,
                status="active",
            )
            db.add(c)
            db.commit()

    return ok({"msg": f"已将 {u.real_name} 设为 {body.role}"})


class ResetPwIn(BaseModel):
    new_password: str


@router.post("/users/{uid}/reset-password")
def reset_password(
    uid: int,
    body: ResetPwIn,
    db: Session = Depends(get_db),
    current=Depends(require_super_admin),
):
    """超管重置任意用户密码"""
    import bcrypt
    u = db.query(AdminUser).filter(AdminUser.id == uid).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    u.password_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    log_operation(db, current, "reset_password", "admin_user", uid, f"重置 {u.real_name} 密码")
    db.commit()
    return ok({"msg": "密码已重置"})


@router.post("/users/{uid}/disable")
def disable_user(
    uid: int,
    db: Session = Depends(get_db),
    current=Depends(require_super_admin),
):
    """停用账号"""
    u = db.query(AdminUser).filter(AdminUser.id == uid).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    u.status = "disabled"
    log_operation(db, current, "disable_user", "admin_user", uid, f"停用 {u.real_name}")
    db.commit()
    return ok({"msg": "已停用"})


# ---------- 分公司管理 ----------
@router.get("/branches")
def list_branches(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    q = db.query(Branch)
    if status:
        q = q.filter(Branch.status == status)
    rows = q.order_by(Branch.id.asc()).all()
    return ok([to_dict(r) for r in rows])


@router.post("/branches")
def create_branch(
    body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    b = Branch(
        name=body.get('name', ''),
        short_name=body.get('short_name', ''),
        city=body.get('city', ''),
        address=body.get('address', ''),
        contact_name=body.get('contact_name', ''),
        contact_phone=body.get('contact_phone', ''),
        established_date=body.get('established_date', ''),
        status=body.get('status', 'active'),
        remark=body.get('remark', ''),
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return ok(to_dict(b))


@router.put("/branches/{bid}")
def update_branch(
    bid: int,
    body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    b = db.query(Branch).filter(Branch.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="分公司不存在")
    for k in ['name', 'short_name', 'city', 'address', 'contact_name', 'contact_phone', 'established_date', 'status', 'remark']:
        if k in body:
            setattr(b, k, body[k])
    db.commit()
    db.refresh(b)
    return ok(to_dict(b))


@router.delete("/branches/{bid}")
def delete_branch(
    bid: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    b = db.query(Branch).filter(Branch.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="分公司不存在")
    b.status = 'closed'
    db.commit()
    return ok({'msg': '已关闭'})


# ---------- 操作日志 ----------
@router.get("/operation-logs")
def operation_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    total = db.execute(text("SELECT count(*) FROM operation_logs")).scalar() or 0
    rows = db.execute(text(
        "SELECT id,admin_id,admin_name,action,target_type,target_id,detail,created_at "
        "FROM operation_logs ORDER BY id DESC LIMIT :lim OFFSET :off"
    ), {"lim": size, "off": (page - 1) * size}).mappings().all()
    items = [{"id": r["id"], "admin_id": r["admin_id"], "admin_name": r["admin_name"],
              "action": r["action"], "target_type": r["target_type"], "target_id": r["target_id"],
              "detail": r["detail"], "created_at": str(r["created_at"]) if r["created_at"] else None}
             for r in rows]
    return {"items": items, "total": total}


# ---------- 回收站 ----------
@router.get("/recycle-bin")
def recycle_bin(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    target_type: str = Query(""),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    where = ""
    params: dict = {"lim": size, "off": (page - 1) * size}
    if target_type:
        where = " WHERE target_type = :tt"
        params["tt"] = target_type
    total = db.execute(text(f"SELECT count(*) FROM recycle_bin{where}"), params).scalar() or 0
    rows = db.execute(text(
        f"SELECT id,target_type,target_id,target_name,deleted_by,deleted_by_name,deleted_at "
        f"FROM recycle_bin{where} ORDER BY id DESC LIMIT :lim OFFSET :off"
    ), params).mappings().all()
    items = [{"id": r["id"], "target_type": r["target_type"], "target_id": r["target_id"],
              "target_name": r["target_name"], "deleted_by": r["deleted_by"],
              "deleted_by_name": r["deleted_by_name"],
              "deleted_at": str(r["deleted_at"]) if r["deleted_at"] else None}
             for r in rows]
    return {"items": items, "total": total}


@router.post("/recycle-bin/{rid}/restore")
def recycle_restore(
    rid: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_admin_or_agent),
):
    row = db.execute(text("SELECT * FROM recycle_bin WHERE id = :rid"), {"rid": rid}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    import json as _json
    snapshot = _json.loads(row["snapshot"]) if row["snapshot"] else {}
    target_type = row["target_type"]
    if target_type == "member" and snapshot:
        # 恢复学员：重新插入
        cols_skip = {"id"}
        cols = [k for k in snapshot if k not in cols_skip and not k.startswith("tier_info")]
        col_str = ", ".join(cols)
        val_str = ", ".join([f":{c}" for c in cols])
        try:
            db.execute(text(f"INSERT INTO members({col_str}) VALUES({val_str})"),
                       {c: snapshot.get(c) for c in cols})
        except Exception:
            raise HTTPException(status_code=400, detail="恢复失败，可能存在冲突")
    db.execute(text("DELETE FROM recycle_bin WHERE id = :rid"), {"rid": rid})
    # 操作日志
    db.execute(text(
        "INSERT INTO operation_logs(admin_id,admin_name,action,target_type,target_id,detail) "
        "VALUES(:aid,:aname,:act,:tt,:tid,:det)"
    ), {"aid": admin.id, "aname": admin.username, "act": "恢复",
        "tt": target_type, "tid": row["target_id"],
        "det": f"从回收站恢复「{row['target_name']}」"})
    db.commit()
    return ok({"restored": rid})


# ──────────── 老师月度统计 ────────────
@router.get("/consultants/{cid}/monthly-stats")
def consultant_monthly_stats(
    cid: int,
    year: int = None,
    month: int = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent)
):
    """查询老师月度统计数据"""
    import datetime
    from models.service import ServiceOrder
    from sqlalchemy import and_

    now = datetime.date.today()
    if not year:
        year = now.year
    if not month:
        month = now.month

    c = db.query(Consultant).filter(Consultant.id == cid).first()
    if not c:
        raise HTTPException(404, "老师不存在")

    first_day = datetime.date(year, month, 1)
    if month == 12:
        last_day = datetime.date(year + 1, 1, 1)
    else:
        last_day = datetime.date(year, month + 1, 1)

    # 主案出差天数：service_orders 中作为主顾问、本月排期日
    try:
        main_days = (
            db.query(func.count(func.distinct(ServiceOrder.appoint_date)))
            .filter(
                ServiceOrder.consultant_id == cid,
                ServiceOrder.appoint_date >= first_day,
                ServiceOrder.appoint_date < last_day,
                ServiceOrder.status.notin_([cancelled, rejected]),
            ).scalar() or 0
        )
    except:
        main_days = 0

    # 助理出差天数
    try:
        assist_days = (
            db.query(func.count(func.distinct(ServiceOrder.appoint_date)))
            .filter(
                ServiceOrder.assistant_id == cid,
                ServiceOrder.appoint_date >= first_day,
                ServiceOrder.appoint_date < last_day,
                ServiceOrder.status.notin_([cancelled, rejected]),
            ).scalar() or 0
        )
    except:
        assist_days = 0

    # 归属会员数
    from models.member import Member
    try:
        member_count = (
            db.query(func.count(Member.id))
            .filter(Member.consultant_id == cid)
            .scalar() or 0
        )
    except:
        member_count = 0

    # 正在跟进客户数
    try:
        active_clients = (
            db.query(func.count(func.distinct(ServiceOrder.member_id)))
            .filter(
                ServiceOrder.consultant_id == cid,
                ServiceOrder.status.in_([accepted, in_progress, preparing, reporting, follow_up]),
            ).scalar() or 0
        )
    except:
        active_clients = 0

    # 主案服务客户数（本月）
    try:
        main_clients = (
            db.query(func.count(func.distinct(ServiceOrder.member_id)))
            .filter(
                ServiceOrder.consultant_id == cid,
                ServiceOrder.created_at >= first_day,
                ServiceOrder.created_at < last_day,
            ).scalar() or 0
        )
    except:
        main_clients = 0

    # 助理服务客户数（本月）
    try:
        assist_clients = (
            db.query(func.count(func.distinct(ServiceOrder.member_id)))
            .filter(
                ServiceOrder.assistant_id == cid,
                ServiceOrder.created_at >= first_day,
                ServiceOrder.created_at < last_day,
            ).scalar() or 0
        )
    except:
        assist_clients = 0

    # 销售额（pay_type=sale, pay_status=completed）
    from models.member import Payment
    try:
        sales = float(
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.consultant_id == cid,
                Payment.pay_type == "sale",
                Payment.pay_status == "completed",
                Payment.created_at >= first_day,
                Payment.created_at < last_day,
            ).scalar() or 0
        )
    except:
        sales = 0.0

    # 消耗额
    try:
        consumption = float(
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.consultant_id == cid,
                Payment.pay_type == "consumption",
                Payment.pay_status == "completed",
                Payment.created_at >= first_day,
                Payment.created_at < last_day,
            ).scalar() or 0
        )
    except:
        consumption = 0.0

    # 课程报名人数（本月该老师名下的报名数）
    from models.course_session import CourseEnrollment, CourseSession
    try:
        course_enrolled = (
            db.query(func.count(CourseEnrollment.id))
            .filter(
                CourseEnrollment.consultant_id == cid,
                CourseEnrollment.created_at >= first_day,
                CourseEnrollment.created_at < last_day,
            ).scalar() or 0
        )
    except:
        course_enrolled = 0

    # 参加课程人数（本月该老师名下、已签到/已完成的）
    try:
        course_attended = (
            db.query(func.count(CourseEnrollment.id))
            .filter(
                CourseEnrollment.consultant_id == cid,
                CourseEnrollment.created_at >= first_day,
                CourseEnrollment.created_at < last_day,
                CourseEnrollment.status.in_([checked_in, completed, follow_up, closed]),
            ).scalar() or 0
        )
    except:
        course_attended = 0

    return ok({
        "consultant_id": cid,
        "consultant_name": c.name,
        "year": year,
        "month": month,
        "main_days": int(main_days),
        "assist_days": int(assist_days),
        "member_count": int(member_count),
        "active_clients": int(active_clients),
        "main_clients": int(main_clients),
        "assist_clients": int(assist_clients),
        "sales": sales,
        "consumption": consumption,
        "course_enrolled": int(course_enrolled),
        "course_attended": int(course_attended),
    })
