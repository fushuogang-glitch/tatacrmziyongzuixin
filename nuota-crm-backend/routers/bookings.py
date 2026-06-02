# 下店预约
from datetime import datetime, date as date_type, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import VisitBooking, VisitReward, Member, Consultant, AdminUser
from models.booking import ConsultantSchedule
from schemas.api import BookingApplyIn, BookingConfirmIn, BookingCompleteIn
from services.quota_service import has_quota, quota_summary, set_monthly_cap
from services.notify_service import notify_booking_confirmed, notify_booking_applied
from routers.notifications import push_to_all_admins
from utils.auth import get_current_member, get_current_admin, get_current_admin_or_consultant
from utils.auth import get_admin_or_agent
from utils.helpers import ok, to_dict


router = APIRouter(prefix="/api/bookings", tags=["bookings"])
admin_router = APIRouter(prefix="/admin/bookings", tags=["admin-bookings"])
quota_router = APIRouter(prefix="/admin/quota", tags=["admin-quota"])


@router.post("/apply")
def apply_booking(body: BookingApplyIn, db: Session = Depends(get_db),
                  current: Member = Depends(get_current_member)):
    reward = (
        db.query(VisitReward)
        .filter(VisitReward.id == body.reward_id, VisitReward.member_id == current.id)
        .first()
    )
    if not reward:
        raise HTTPException(status_code=404, detail="权益不存在")
    if reward.status != "available":
        raise HTTPException(status_code=400, detail="权益不可用")

    if not has_quota(db, body.preferred_date):
        raise HTTPException(status_code=400, detail="该月名额已满，请选择下月")

    booking = VisitBooking(
        member_id=current.id,
        reward_id=reward.id,
        preferred_date=body.preferred_date,
        city=body.city,
        address=body.address,
        duration_days=body.duration_days or 2,
        remark=body.remark,
        status="pending",
    )
    db.add(booking)

    reward.status = "booked"
    db.flush()
    reward.booking_id = booking.id
    db.commit()
    db.refresh(booking)

    # 通知管理员
    notify_booking_applied(
        current.name or '',
        current.phone or '',
        str(body.preferred_date),
        body.city or '',
        body.duration_days or 2,
    )
    # 站内通知
    push_to_all_admins(
        db,
        title=f"新下店预约：{current.name or '学员'}",
        body=f"城市 {body.city or '未填'}，期望日期 {body.preferred_date}，{body.duration_days or 2}天",
        ntype="booking",
        ref_type="visit_booking",
        ref_id=booking.id,
    )
    db.commit()

    return ok(to_dict(booking))


@router.get("/my-bookings")
def my_bookings(db: Session = Depends(get_db), current: Member = Depends(get_current_member)):
    rows = (
        db.query(VisitBooking)
        .filter(VisitBooking.member_id == current.id)
        .order_by(VisitBooking.apply_time.desc())
        .all()
    )
    return ok([to_dict(b) for b in rows])


# ---- 管理端 ----
@admin_router.get("")
def admin_list(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    q = db.query(VisitBooking, Member).join(Member, VisitBooking.member_id == Member.id)
    if current_user.is_consultant:
        q = q.filter(VisitBooking.consultant_id == current_user.consultant_id)
    if status:
        q = q.filter(VisitBooking.status == status)
    rows = q.order_by(VisitBooking.apply_time.desc()).all()
    data = []
    for b, m in rows:
        item = to_dict(b)
        item["member"] = {"id": m.id, "name": m.name, "phone": m.phone, "member_no": m.member_no}
        data.append(item)
    return ok(data)


@admin_router.put("/{bid}/confirm")
def admin_confirm(bid: int, body: BookingConfirmIn, db: Session = Depends(get_db),
                  current_user = Depends(get_current_admin_or_consultant)):
    b = db.query(VisitBooking).filter(VisitBooking.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="预约不存在")
    if b.status not in ("pending",):
        raise HTTPException(status_code=400, detail="该状态不可确认")

    # 老师只能确认分配给自己的预约
    consultant_id = body.consultant_id
    if current_user.is_consultant:
        consultant_id = current_user.consultant_id

    c = db.query(Consultant).filter(Consultant.id == consultant_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="顾问不存在")

    if not has_quota(db, body.confirmed_date):
        raise HTTPException(status_code=400, detail="该月名额已满")

    b.consultant_id = consultant_id
    b.confirmed_date = body.confirmed_date
    b.status = "confirmed"

    # 自动创建排期（确认日期开始，连续 duration_days 天）
    duration = b.duration_days or 2
    m = db.query(Member).filter(Member.id == b.member_id).first()
    title = m.enterprise_name or m.name or '' if m else ''
    city = b.city or ''
    for i in range(duration):
        d = body.confirmed_date + timedelta(days=i)
        exists = db.query(ConsultantSchedule).filter(
            ConsultantSchedule.consultant_id == consultant_id,
            ConsultantSchedule.schedule_date == d,
        ).first()
        if not exists:
            s = ConsultantSchedule(
                consultant_id=consultant_id,
                schedule_date=d,
                city=city,
                schedule_type='busy',
                title=title,
                remark=f'下店预约#{b.id} 自动排期',
                created_by=current_user.user_id,
            )
            db.add(s)

    db.commit()

    if m:
        notify_booking_confirmed(m.name or "", m.phone or "", c.name or "", str(body.confirmed_date))

    return ok(to_dict(b))


@admin_router.put("/{bid}/complete")
def admin_complete(bid: int, body: BookingCompleteIn, db: Session = Depends(get_db),
                   _: AdminUser = Depends(get_admin_or_agent)):
    b = db.query(VisitBooking).filter(VisitBooking.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="预约不存在")
    if b.status != "confirmed":
        raise HTTPException(status_code=400, detail="未确认的预约不可完成")
    b.status = "completed"
    b.complete_time = datetime.utcnow()
    if body.member_rating:
        b.member_rating = body.member_rating

    reward = db.query(VisitReward).filter(VisitReward.id == b.reward_id).first()
    if reward:
        reward.status = "used"
        reward.used_time = b.complete_time

    db.commit()
    return ok(to_dict(b))


@admin_router.put("/{bid}/cancel")
def admin_cancel(bid: int, db: Session = Depends(get_db),
                 _: AdminUser = Depends(get_admin_or_agent)):
    b = db.query(VisitBooking).filter(VisitBooking.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="预约不存在")
    if b.status == "completed":
        raise HTTPException(status_code=400, detail="已完成不可取消")
    b.status = "cancelled"
    # 归还权益
    reward = db.query(VisitReward).filter(VisitReward.id == b.reward_id).first()
    if reward and reward.status == "booked":
        reward.status = "available"
        reward.booking_id = None
    db.commit()
    return ok(to_dict(b))


# ---- 名额 ----
@quota_router.get("/monthly")
def monthly(
    year: int, month: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    return ok(quota_summary(db, year, month))


@quota_router.put("/set")
def set_cap(
    year: int, month: int, cap: int,
    _: AdminUser = Depends(get_admin_or_agent),
):
    set_monthly_cap(year, month, cap)
    return ok({"year": year, "month": month, "cap": cap})
