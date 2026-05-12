# 课程手册 + 后台账号
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from database import Base


class Handbook(Base):
    """课程手册表 handbooks"""
    __tablename__ = "handbooks"
    __table_args__ = (UniqueConstraint("member_id", "session_id", name="uq_handbooks_member_session"),)

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    day1_data = Column(JSONB)
    day2_data = Column(JSONB)
    day3_data = Column(JSONB)
    is_complete = Column(Boolean, default=False)
    sign_time = Column(DateTime)
    consultant_id = Column(Integer, ForeignKey("consultants.id"))
    created_at = Column(DateTime, server_default=func.now())


class AdminUser(Base):
    """后台管理账号 admin_users（非 PRD 原表，但后台登录必须）。"""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50))
    phone = Column(String(20))
    role = Column(String(20), default="admin")                 # admin/operator
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())
