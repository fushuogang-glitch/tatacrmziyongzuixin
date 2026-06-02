# 下店预约 + 顾问
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func

from database import Base


class Consultant(Base):
    """顾问表 consultants"""
    __tablename__ = "consultants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    phone = Column(String(20))
    specialty = Column(String(100), nullable=True)   # 专业领域
    company = Column(String(100), nullable=True)     # 所属分公司
    service_modules = Column(Text, nullable=True)    # JSON 多选服务模块
    password_hash = Column(String(128), nullable=True)  # 顾问登录密码
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


class ConsultantSchedule(Base):
    """老师排期表 consultant_schedules"""
    __tablename__ = "consultant_schedules"

    id = Column(Integer, primary_key=True, index=True)
    consultant_id = Column(Integer, ForeignKey("consultants.id"), index=True)
    schedule_date = Column(Date, index=True)           # 排期日期
    city = Column(String(50))                          # 城市/地点
    schedule_type = Column(String(20), default="available")  # available/busy/leave
    title = Column(String(100))                        # 备注标题（如「成都出差」）
    remark = Column(Text)
    order_id = Column(Integer, index=True)   # 关联工单ID（service_orders.id，不做 FK 避免循环引用）
    created_by = Column(Integer)                       # 操作管理员ID
    created_at = Column(DateTime, server_default=func.now())


class ConsultantApplication(Base):
    """顾问注册申请表 consultant_applications"""
    __tablename__ = "consultant_applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False, unique=True)
    specialty = Column(String(100), nullable=True)
    company = Column(String(100), nullable=True)
    service_modules = Column(Text, nullable=True)          # JSON 存多选
    password_hash = Column(String(128), nullable=False)
    status = Column(String(20), default="pending")         # pending/approved/rejected
    reviewed_by = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    review_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ConsultantInviteCode(Base):
    """顾问邀请码表 consultant_invite_codes"""
    __tablename__ = "consultant_invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    consultant_id = Column(Integer, ForeignKey("consultants.id"), index=True)
    code = Column(String(32), unique=True, index=True)
    used_count = Column(Integer, default=0)
    max_uses = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
