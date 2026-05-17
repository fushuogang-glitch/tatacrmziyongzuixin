# 管理后台：学员 / 顾问 / 缴费 / 看板
from datetime import date, datetime, timedelta
import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, extract, text
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Member, Payment, Session as SessionModel, Enrollment,
    Referral, VisitReward, VisitBooking, Consultant, AdminUser,
    Service, ServicePackage, PackageConsumption,
)
from models.booking import ConsultantSchedule
from models.branch import Branch
from schemas.api import (
    MemberRegisterIn, MemberUpdateIn, PaymentCreateIn, ConsultantIn,
)
from services.referral_service import bind_referral, confirm_referral_on_payment
from services.notify_service import notify_referral_reward
from utils.auth import get_current_admin, get_current_admin_or_consultant
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


def require_super_admin(current: AdminUser = Depends(get_current_admin)):
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
    _: AdminUser = Depends(get_current_admin),
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
                   _: AdminUser = Depends(get_current_admin)):
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
                  _: AdminUser = Depends(get_current_admin)):
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
                  _: AdminUser = Depends(get_current_admin)):
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
                  _: AdminUser = Depends(get_current_admin)):
    m = db.query(Member).filter(Member.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="学员不存在")
    return ok(_member_out(m, db))


@router.delete("/members/{mid}")
def delete_member(mid: int, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(get_current_admin)):
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
                   _: AdminUser = Depends(get_current_admin)):
    m = db.query(Member).filter(Member.id == body.member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="学员不存在")

    # 如果未指定归属老师，自动继承学员的归属老师
    cid = body.consultant_id or m.consultant_id
    p = Payment(
        member_id=body.member_id,
        consultant_id=cid,
        amount=body.amount,
        debt_amount=body.debt_amount or 0,
        pay_mode=body.pay_mode or "full",
        pay_method=body.pay_method,
        pay_type=body.pay_type,
        pay_status=body.pay_status,
        service_id=body.service_id,
        pay_time=datetime.utcnow() if body.pay_status in ("paid", "partial") else None,
        due_date=date.fromisoformat(body.due_date) if body.due_date else None,
        remark=body.remark,
    )
    db.add(p)

    # 同步更新学员归属老师（如果提供了）
    if body.consultant_id and body.consultant_id != m.consultant_id:
        m.consultant_id = body.consultant_id

    if body.pay_status in ("paid", "partial"):
        if body.pay_type == "annual":
            m.member_type = "annual"
            m.enroll_date = m.enroll_date or date.today()

        # ---- 自动创建套餐 ----
        total_times = body.total_times
        if body.pay_type == "annual":
            total_times = total_times or 6  # 年费制默认6次
        elif body.pay_type == "single" and body.service_id:
            svc = db.query(Service).filter(Service.id == body.service_id).first()
            total_times = total_times or (svc.total_times if svc and svc.total_times else 1)
        else:
            total_times = total_times or 1

        per_time_fee = round(float(body.amount) / total_times, 2) if total_times else float(body.amount)

        pkg_no = f"PKG-{date.today().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        pkg = ServicePackage(
            member_id=body.member_id,
            package_no=pkg_no,
            total_times=total_times,
            used_times=0,
            amount=body.amount,
            per_time_fee=per_time_fee,
            pay_type=body.pay_type,
            start_date=date.today(),
            expire_date=date.today() + timedelta(days=365) if body.pay_type == "annual" else None,
            status="active",
        )
        db.add(pkg)
        db.flush()  # 获取 pkg.id
        p.package_id = pkg.id

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
    _: AdminUser = Depends(get_current_admin),
):
    q = db.query(Payment)
    if member_id:
        q = q.filter(Payment.member_id == member_id)
    payments = q.order_by(Payment.id.desc()).limit(500).all()

    # 关联查询学员和老师名称
    member_ids = list({p.member_id for p in payments if p.member_id})
    consultant_ids = list({p.consultant_id for p in payments if p.consultant_id})
    members_map = {m.id: m for m in db.query(Member).filter(Member.id.in_(member_ids)).all()} if member_ids else {}
    consultants_map = {c.id: c for c in db.query(Consultant).filter(Consultant.id.in_(consultant_ids)).all()} if consultant_ids else {}

    result = []
    for p in payments:
        d = to_dict(p)
        m = members_map.get(p.member_id)
        c = consultants_map.get(p.consultant_id) if p.consultant_id else None
        d['member_name'] = m.name if m else ''
        d['enterprise_name'] = getattr(m, 'enterprise_name', '') if m else ''
        d['member_phone'] = m.phone if m else ''
        d['consultant_name'] = c.name if c else ''

        # 套餐扣费明细
        if p.package_id:
            pkg = db.query(ServicePackage).filter(ServicePackage.id == p.package_id).first()
            if pkg:
                d['total_times'] = pkg.total_times
                d['used_times'] = pkg.used_times
                d['remaining_times'] = pkg.total_times - pkg.used_times
                d['per_time_fee'] = float(pkg.per_time_fee) if pkg.per_time_fee else 0
                d['pay_type_label'] = '年费制' if pkg.pay_type == 'annual' else '单次制'
            else:
                d['total_times'] = d['used_times'] = d['remaining_times'] = 0
                d['per_time_fee'] = 0
                d['pay_type_label'] = '-'
        else:
            d['total_times'] = d['used_times'] = d['remaining_times'] = 0
            d['per_time_fee'] = 0
            d['pay_type_label'] = '-'

        # 合作项目名称
        if getattr(p, 'service_id', None):
            svc = db.query(Service).filter(Service.id == p.service_id).first()
            d['service_name'] = svc.name if svc else '-'
        else:
            d['service_name'] = '-'

        result.append(d)
    return ok(result)


# ---------- 消耗明细 ----------
@router.get("/services/consumptions")
def list_consumptions(
    member_id: Optional[int] = None,
    package_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
):
    q = db.query(PackageConsumption)
    if member_id:
        q = q.filter(PackageConsumption.member_id == member_id)
    if package_id:
        q = q.filter(PackageConsumption.package_id == package_id)
    items = q.order_by(PackageConsumption.id.desc()).limit(500).all()
    return ok([to_dict(c) for c in items])


# ---------- 顾问 ----------
@router.get("/consultants")
def list_consultants(db: Session = Depends(get_db),
                     _: AdminUser = Depends(get_current_admin)):
    rows = db.query(Consultant).order_by(Consultant.id.asc()).all()
    return ok([to_dict(c) for c in rows])


@router.post("/consultants")
def create_consultant(body: ConsultantIn, db: Session = Depends(get_db),
                      current: AdminUser = Depends(get_current_admin)):
    # 管理员只能新增本公司顾问
    role = getattr(current, 'role', 'admin')
    if role != 'super_admin':
        admin_company = getattr(current, 'company', None)
        if not admin_company or body.company != admin_company:
            raise HTTPException(status_code=403, detail="只能新增本公司顾问")
    c = Consultant(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    log_operation(db, current, '新增顾问', 'consultant', c.id, f'姓名:{c.name} 公司:{c.company}')
    return ok(to_dict(c))


@router.put("/consultants/{cid}")
def update_consultant(cid: int, body: ConsultantIn, db: Session = Depends(get_db),
                      current: AdminUser = Depends(get_current_admin)):
    c = db.query(Consultant).filter(Consultant.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="顾问不存在")
    # 权限检查：管理员只能改本公司顾问
    check_company_permission(current, c.company or '')
    old_info = f'姓名:{c.name} 公司:{c.company}'
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    log_operation(db, current, '修改顾问', 'consultant', c.id, f'原:{old_info} 新:姓名:{c.name}')
    return ok(to_dict(c))


@router.delete("/consultants/{cid}")
def delete_consultant(cid: int, db: Session = Depends(get_db),
                      current: AdminUser = Depends(get_current_admin)):
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
              _: AdminUser = Depends(get_current_admin)):
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

    # 下店统计：按品牌/企业去重计数 + 总天数
    # 排期表：按 title 去重 = 品牌数，count = 总天数
    from sqlalchemy import distinct
    schedule_brands = (
        db.query(func.count(distinct(ConsultantSchedule.title)))
        .filter(ConsultantSchedule.schedule_type == "busy",
                ConsultantSchedule.title.isnot(None),
                ConsultantSchedule.title != "",
                extract("year", ConsultantSchedule.schedule_date) == y,
                extract("month", ConsultantSchedule.schedule_date) == mo)
        .scalar() or 0
    )
    schedule_days = (
        db.query(func.count(ConsultantSchedule.id))
        .filter(ConsultantSchedule.schedule_type == "busy",
                extract("year", ConsultantSchedule.schedule_date) == y,
                extract("month", ConsultantSchedule.schedule_date) == mo)
        .scalar() or 0
    )
    # 下店预约表：按 member_id 去重
    booking_brands = (
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
    month_visit = schedule_brands + booking_brands      # 品牌/企业数
    month_visit_days = schedule_days + booking_days      # 总天数
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


# ──────────────────── 菜单徽标 ────────────────────

@router.get("/stats/menu-badges")
def menu_badges(db: Session = Depends(get_db),
                _: AdminUser = Depends(get_current_admin)):
    """返回侧栏菜单徽标数字"""
    pending_bookings = (
        db.query(func.count(VisitBooking.id))
        .filter(VisitBooking.status == "pending")
        .scalar() or 0
    )
    pending_rewards = (
        db.query(func.count(VisitReward.id))
        .filter(VisitReward.status == "available")
        .scalar() or 0
    )
    return ok({
        "bookings": int(pending_bookings),
        "rewards": int(pending_rewards),
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
    _: AdminUser = Depends(get_current_admin),
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
    _: AdminUser = Depends(get_current_admin),
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
    _: AdminUser = Depends(get_current_admin),
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
    _: AdminUser = Depends(get_current_admin),
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
    _: AdminUser = Depends(get_current_admin),
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
    _: AdminUser = Depends(get_current_admin),
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
    admin: AdminUser = Depends(get_current_admin),
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
