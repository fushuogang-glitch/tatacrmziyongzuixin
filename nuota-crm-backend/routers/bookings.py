# 下店预约
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import VisitBooking, VisitReward, Member, Consultant, AdminUser
from schemas.api import BookingApplyIn, BookingConfirmIn, BookingCompleteIn
from services.quota_service import has_quota, quota_summary, set_monthly_cap
from services.notify_service import notify_booking_confirmed
from utils.auth import get_current_member, get_current_admin
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
    _: AdminUser = Depends(get_current_admin),
):
    q = db.query(VisitBooking, Member).join(Member, VisitBooking.member_id == Member.id)
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
                  _: AdminUser = Depends(get_current_admin)):
    b = db.query(VisitBooking).filter(VisitBooking.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="预约不存在")
    if b.status not in ("pending",):
        raise HTTPException(status_code=400, detail="该状态不可确认")

    c = db.query(Consultant).filter(Consultant.id == body.consultant_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="顾问不存在")

    if not has_quota(db, body.confirmed_date):
        raise HTTPException(status_code=400, detail="该月名额已满")

    b.consultant_id = body.consultant_id
    b.confirmed_date = body.confirmed_date
    b.status = "confirmed"
    db.commit()

    m = db.query(Member).filter(Member.id == b.member_id).first()
    if m:
        notify_booking_confirmed(m.name or "", m.phone or "", c.name or "", str(body.confirmed_date))

    return ok(to_dict(b))


@admin_router.put("/{bid}/complete")
def admin_complete(bid: int, body: BookingCompleteIn, db: Session = Depends(get_db),
                   _: AdminUser = Depends(get_current_admin)):
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
                 _: AdminUser = Depends(get_current_admin)):
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
    _: AdminUser = Depends(get_current_admin),
):
    return ok(quota_summary(db, year, month))


@quota_router.put("/set")
def set_cap(
    year: int, month: int, cap: int,
    _: AdminUser = Depends(get_current_admin),
):
    set_monthly_cap(year, month, cap)
    return ok({"year": year, "month": month, "cap": cap})
