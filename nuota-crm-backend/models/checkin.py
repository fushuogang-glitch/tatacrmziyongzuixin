# 签到记录
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from database import Base


class Checkin(Base):
    """签到记录表 checkins"""
    __tablename__ = "checkins"
    __table_args__ = (
        UniqueConstraint("member_id", "session_id", "checkin_day", name="uq_checkins_member_session_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    checkin_day = Column(Integer)                              # 1/2/3
    checkin_time = Column(DateTime, server_default=func.now())
    method = Column(String(20), default="face")                # face/manual
    operator_id = Column(Integer)                              # 手动签到时操作员
