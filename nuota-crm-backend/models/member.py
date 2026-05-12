# 学员/缴费模型
from sqlalchemy import (
    Column, Integer, String, Text, Date, Numeric, DateTime, ForeignKey
)
from sqlalchemy.sql import func

from database import Base


class Member(Base):
    """学员表 members"""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    enterprise_name = Column(String(100))
    city = Column(String(50))
    role = Column(String(20))                                  # boss/manager/consultant
    face_token = Column(Text)                                  # 腾讯云人脸特征 token
    member_type = Column(String(20), default="trial")          # trial/annual/vip
    member_no = Column(String(20), unique=True)                # TT-2026-0001
    enroll_date = Column(Date)
    expire_date = Column(Date)
    referral_code = Column(String(20), unique=True, index=True)
    referred_by = Column(Integer, ForeignKey("members.id"))
    status = Column(String(20), default="active")              # active/expired/frozen
    # 小程序 openid（微信登录映射，字段可空以兼容后台手动录入）
    openid = Column(String(64), unique=True, index=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Payment(Base):
    """缴费记录表 payments"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    amount = Column(Numeric(10, 2))
    pay_type = Column(String(20))                              # trial/annual
    pay_status = Column(String(20), default="pending")         # pending/paid/refunded
    pay_time = Column(DateTime)
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
