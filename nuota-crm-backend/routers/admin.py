# 管理后台：学员 / 顾问 / 缴费 / 看板
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Member, Payment, Session as SessionModel, Enrollment,
    Referral, VisitReward, VisitBooking, Consultant, AdminUser,
)
from schemas.api import (
    MemberRegisterIn, MemberUpdateIn, PaymentCreateIn, ConsultantIn,
)
from services.referral_service import bind_referral, confirm_referral_on_payment
from services.notify_service import notify_referral_reward
from utils.auth import get_current_admin
from utils.helpers import ok, to_dict, gen_member_no, gen_referral_code


router = APIRouter(prefix="/admin", tags=["admin"])


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


@router.post("/members")
def create_member(body: MemberRegisterIn, db: Session = Depends(get_db),
                  _: AdminUser = Depends(get_current_admin)):
    if db.query(Member).filter(Member.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="手机号已存在")
    m = Member(
        name=body.name, phone=body.phone,
        enterprise_name=body.enterprise_name, city=body.city, role=body.role,
        member_type=body.member_type or "trial",
        enroll_date=date.today(), status="active",
    )
    db.add(m)
    db.flush()
    m.member_no = gen_member_no(db)
    m.referral_code = gen_referral_code()
    bind_referral(db, m, body.referral_code)
    db.commit()
    db.refresh(m)
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
    return ok(to_dict(m))


@router.get("/members/{mid}")
def member_detail(mid: int, db: Session = Depends(get_db),
                  _: AdminUser = Depends(get_current_admin)):
    m = db.query(Member).filter(Member.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="学员不存在")
    return ok(to_dict(m))


# ---------- 缴费 ----------
@router.post("/payments")
def create_payment(body: PaymentCreateIn, db: Session = Depends(get_db),
                   _: AdminUser = Depends(get_current_admin)):
    m = db.query(Member).filter(Member.id == body.member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="学员不存在")

    p = Payment(
        member_id=body.member_id,
        amount=body.amount,
        pay_type=body.pay_type,
        pay_status=body.pay_status,
        pay_time=datetime.utcnow() if body.pay_status == "paid" else None,
        remark=body.remark,
    )
    db.add(p)

    if body.pay_status == "paid":
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
    _: AdminUser = Depends(get_current_admin),
):
    q = db.query(Payment)
    if member_id:
        q = q.filter(Payment.member_id == member_id)
    rows = q.order_by(Payment.id.desc()).limit(500).all()
    return ok([to_dict(p) for p in rows])


# ---------- 顾问 ----------
@router.get("/consultants")
def list_consultants(db: Session = Depends(get_db),
                     _: AdminUser = Depends(get_current_admin)):
    rows = db.query(Consultant).order_by(Consultant.id.asc()).all()
    return ok([to_dict(c) for c in rows])


@router.post("/consultants")
def create_consultant(body: ConsultantIn, db: Session = Depends(get_db),
                      _: AdminUser = Depends(get_current_admin)):
    c = Consultant(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return ok(to_dict(c))


@router.put("/consultants/{cid}")
def update_consultant(cid: int, body: ConsultantIn, db: Session = Depends(get_db),
                      _: AdminUser = Depends(get_current_admin)):
    c = db.query(Consultant).filter(Consultant.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="顾问不存在")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return ok(to_dict(c))


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
        .filter(Payment.pay_status == "paid",
                extract("year", Payment.pay_time) == y)
        .scalar() or 0
    )
    month_income = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.pay_status == "paid",
                extract("year", Payment.pay_time) == y,
                extract("month", Payment.pay_time) == mo)
        .scalar() or 0
    )

    total_refer = db.query(func.count(Referral.id)).scalar() or 0
    confirmed_refer = db.query(func.count(Referral.id)).filter(Referral.status == "confirmed").scalar() or 0
    refer_conv = round(confirmed_refer / total_refer * 100, 1) if total_refer else 0.0

    month_visit = (
        db.query(func.count(VisitBooking.id))
        .filter(VisitBooking.status.in_(["confirmed", "completed"]),
                extract("year", VisitBooking.confirmed_date) == y,
                extract("month", VisitBooking.confirmed_date) == mo)
        .scalar() or 0
    )
    reward_pending = db.query(func.count(VisitReward.id)).filter(VisitReward.status == "available").scalar() or 0

    return ok({
        "total_members": int(total_members),
        "new_this_month": int(new_this_month),
        "trial_conv": trial_conv,
        "year_income": float(year_income),
        "month_income": float(month_income),
        "refer_conv": refer_conv,
        "month_visit": int(month_visit),
        "reward_pending": int(reward_pending),
    })
