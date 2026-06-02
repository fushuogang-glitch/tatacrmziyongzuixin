# 分公司模型
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from database import Base


class Branch(Base):
    """分公司表 branches"""
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)          # 分公司名称（如：上海分公司）
    short_name = Column(String(50))                     # 简称（如：上海）
    city = Column(String(50))                           # 所在城市
    address = Column(String(200))                       # 详细地址
    contact_name = Column(String(50))                   # 负责人姓名
    contact_phone = Column(String(20))                  # 负责人手机
    established_date = Column(String(20))               # 成立日期 YYYY-MM-DD
    status = Column(String(20), default="active")       # active/closed
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
