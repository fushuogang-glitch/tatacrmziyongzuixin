# 企业 & 邀请码
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Enterprise(Base):
    __tablename__ = "enterprises"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    short_name = Column(String(100))
    city = Column(String(100))
    address = Column(Text)
    contact_phone = Column(String(30))
    boss_member_id = Column(Integer)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EnterpriseInvite(Base):
    __tablename__ = "enterprise_invites"
    id = Column(Integer, primary_key=True, index=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    role = Column(String(30), default="manager")
    created_by = Column(Integer)
    max_uses = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())
