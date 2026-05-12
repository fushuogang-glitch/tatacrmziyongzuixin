# 推荐链 + 权益触发
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import Member, Referral, VisitReward


REWARD_EXPIRE_MONTHS = 24


def bind_referral(db: Session, referee: Member, referral_code: Optional[str]) -> Optional[Referral]:
    """学员注册时如果带了推荐码，创建 referrals 记录，默认 pending。"""
    if not referral_code:
        return None
    referrer = db.query(Member).filter(Member.referral_code == referral_code).first()
    if not referrer or referrer.id == referee.id:
        return None
    if referee.referred_by:
        return None
    referee.referred_by = referrer.id
    ref = Referral(
        referrer_id=referrer.id,
        referee_id=referee.id,
        status="pending",
        reward_type="visit_once",
        reward_status="pending",
    )
    db.add(ref)
    db.flush()
    return ref


def confirm_referral_on_payment(db: Session, referee_id: int) -> Optional[VisitReward]:
    """被推荐人缴费成功 -> 激活推荐关系 + 触发推荐人下店权益。"""
    ref = (
        db.query(Referral)
        .filter(Referral.referee_id == referee_id, Referral.status == "pending")
        .first()
    )
    if not ref:
        return None

    now = datetime.utcnow()
    ref.status = "confirmed"
    ref.confirm_time = now
    ref.reward_status = "activated"

    reward = VisitReward(
        member_id=ref.referrer_id,
        source="referral",
        referral_id=ref.id,
        status="available",
        activate_time=now,
        expire_time=now + timedelta(days=REWARD_EXPIRE_MONTHS * 30),
    )
    db.add(reward)
    db.flush()
    return reward


def admin_confirm_referral(db: Session, referral_id: int) -> Optional[VisitReward]:
    """后台手动确认推荐成立，同 confirm_referral_on_payment 逻辑。"""
    ref = db.query(Referral).filter(Referral.id == referral_id).first()
    if not ref or ref.status == "confirmed":
        return None
    now = datetime.utcnow()
    ref.status = "confirmed"
    ref.confirm_time = now
    ref.reward_status = "activated"
    reward = VisitReward(
        member_id=ref.referrer_id,
        source="referral",
        referral_id=ref.id,
        status="available",
        activate_time=now,
        expire_time=now + timedelta(days=REWARD_EXPIRE_MONTHS * 30),
    )
    db.add(reward)
    db.flush()
    return reward
