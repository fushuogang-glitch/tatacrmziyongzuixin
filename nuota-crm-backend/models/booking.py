# 下店预约 + 顾问
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class Consultant(Base):
    """顾问表 consultants"""
    __tablename__ = "consultants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    phone = Column(String(20))
    monthly_days = Column(Integer, default=14)
    course_days = Column(Integer, default=8)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())


class VisitBooking(Base):
    """下店预约表 visit_bookings"""
    __tablename__ = "visit_bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    reward_id = Column(Integer, ForeignKey("visit_rewards.id"))
    consultant_id = Column(Integer, ForeignKey("consultants.id"), index=True)
    apply_time = Column(DateTime, server_default=func.now())
    preferred_date = Column(Date)
    confirmed_date = Column(Date, index=True)
    status = Column(String(20), default="pending")             # pending/confirmed/completed/cancelled
    duration_days = Column(Integer, default=2)
    city = Column(String(50))
    address = Column(Text)
    remark = Column(Text)
    complete_time = Column(DateTime)
    member_rating = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
