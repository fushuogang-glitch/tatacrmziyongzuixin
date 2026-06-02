# 推荐相关
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Member, Referral, AdminUser
from services.referral_service import admin_confirm_referral
from services.notify_service import notify_referral_reward
from utils.auth import get_current_member, get_current_admin
from utils.auth import get_admin_or_agent
from utils.helpers import ok, to_dict


router = APIRouter(prefix="/api/referrals", tags=["referrals"])
admin_router = APIRouter(prefix="/admin/referrals", tags=["admin-referrals"])


@router.get("/my-code")
def my_code(current: Member = Depends(get_current_member)):
    return ok({
        "referral_code": current.referral_code,
        "share_text": f"我正在参加诺控·塔塔课程，用我的推荐码 {current.referral_code} 报名享权益。",
    })


@router.get("/my-list")
def my_list(db: Session = Depends(get_db), current: Member = Depends(get_current_member)):
    rows = (
        db.query(Referral, Member)
        .join(Member, Referral.referee_id == Member.id)
        .filter(Referral.referrer_id == current.id)
        .order_by(Referral.created_at.desc())
        .all()
    )
    data = []
    for r, m in rows:
        data.append({
            "id": r.id,
            "status": r.status,
            "reward_status": r.reward_status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "confirm_time": r.confirm_time.isoformat() if r.confirm_time else None,
            "referee": {"id": m.id, "name": m.name, "phone": m.phone},
        })
    return ok(data)


# ---- 管理端 ----
@admin_router.get("")
def admin_list(db: Session = Depends(get_db), _: AdminUser = Depends(get_admin_or_agent)):
    from sqlalchemy.orm import aliased
    Referrer = aliased(Member)
    Referee = aliased(Member)
    rows = (
        db.query(Referral, Referrer, Referee)
        .outerjoin(Referrer, Referral.referrer_id == Referrer.id)
        .outerjoin(Referee, Referral.referee_id == Referee.id)
        .order_by(Referral.created_at.desc())
        .all()
    )
    data = []
    for r, referrer, referee in rows:
        d = to_dict(r)
        d["referrer_name"] = referrer.name if referrer else "未知"
        d["referrer_phone"] = referrer.phone if referrer else ""
        d["referee_name"] = referee.name if referee else "未知"
        d["referee_phone"] = referee.phone if referee else ""
        data.append(d)
    return ok(data)


@admin_router.put("/{rid}/confirm")
def admin_confirm(rid: int, db: Session = Depends(get_db),
                  _: AdminUser = Depends(get_admin_or_agent)):
    reward = admin_confirm_referral(db, rid)
    if not reward:
        raise HTTPException(status_code=400, detail="推荐不存在或已确认")
    db.commit()

    referrer = db.query(Member).filter(Member.id == reward.member_id).first()
    if referrer:
        notify_referral_reward(referrer.name or "", referrer.phone or "")

    return ok({"reward_id": reward.id})
