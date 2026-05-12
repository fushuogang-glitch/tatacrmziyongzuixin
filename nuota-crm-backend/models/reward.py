# 下店权益
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class VisitReward(Base):
    """下店权益表 visit_rewards"""
    __tablename__ = "visit_rewards"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    source = Column(String(20))                                # referral
    referral_id = Column(Integer, ForeignKey("referrals.id"))
    status = Column(String(20), default="available")           # available/booked/used/expired
    activate_time = Column(DateTime)
    expire_time = Column(DateTime)                             # 激活后 24 个月
    used_time = Column(DateTime)
    # 循环外键：use_alter 推迟创建以避免建表循环
    booking_id = Column(
        Integer,
        ForeignKey("visit_bookings.id", use_alter=True, name="fk_visit_rewards_booking_id"),
    )
    created_at = Column(DateTime, server_default=func.now())
