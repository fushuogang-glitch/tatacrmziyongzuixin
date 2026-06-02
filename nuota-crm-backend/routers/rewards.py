# 权益
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import VisitReward, Member, AdminUser
from utils.auth import get_current_member, get_current_admin
from utils.auth import get_admin_or_agent
from utils.helpers import ok, to_dict


router = APIRouter(prefix="/api/rewards", tags=["rewards"])
admin_router = APIRouter(prefix="/admin/rewards", tags=["admin-rewards"])


@router.get("/my-rewards")
def my_rewards(db: Session = Depends(get_db), current: Member = Depends(get_current_member)):
    rows = (
        db.query(VisitReward)
        .filter(VisitReward.member_id == current.id)
        .order_by(VisitReward.created_at.desc())
        .all()
    )
    return ok([to_dict(r) for r in rows])


# ---- 管理端 ----
@admin_router.get("")
def admin_list(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    q = db.query(VisitReward, Member).join(Member, VisitReward.member_id == Member.id)
    if status:
        q = q.filter(VisitReward.status == status)
    rows = q.order_by(VisitReward.created_at.desc()).all()
    data = []
    for r, m in rows:
        item = to_dict(r)
        item["member"] = {"id": m.id, "name": m.name, "phone": m.phone, "member_no": m.member_no}
        data.append(item)
    return ok(data)



@admin_router.post("")
def admin_create_reward(
    body: dict,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_admin_or_agent),
):
    """管理员手动创建权益"""
    from datetime import datetime
    reward = VisitReward(
        member_id=body["member_id"],
        source=body.get("source", "manual"),
        referral_id=body.get("referral_id"),
        status=body.get("status", "available"),
        created_at=datetime.now(),
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return ok(to_dict(reward))
