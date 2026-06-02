# 推荐记录
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class Referral(Base):
    """推荐记录表 referrals"""
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("members.id"), index=True)
    referee_id = Column(Integer, ForeignKey("members.id"), index=True)
    status = Column(String(20), default="pending")             # pending/confirmed/invalid
    confirm_time = Column(DateTime)
    reward_type = Column(String(20))                           # visit_once/full_package
    reward_status = Column(String(20), default="pending")      # pending/activated/used/expired
    created_at = Column(DateTime, server_default=func.now())
