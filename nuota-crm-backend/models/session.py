# 课程场次 / 报名
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from database import Base


class Session(Base):
    """课程场次表 sessions"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_no = Column(String(20), unique=True, index=True)
    start_date = Column(Date)
    end_date = Column(Date)
    location = Column(String(100))
    city = Column(String(50))
    capacity = Column(Integer, default=100)
    enrolled = Column(Integer, default=0)
    status = Column(String(20), default="open")                # open/full/closed/finished
    created_at = Column(DateTime, server_default=func.now())


class Enrollment(Base):
    """报名记录表 enrollments"""
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("member_id", "session_id", name="uq_enrollments_member_session"),)

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    enroll_time = Column(DateTime, server_default=func.now())
    status = Column(String(20), default="enrolled")            # enrolled/attended/absent
