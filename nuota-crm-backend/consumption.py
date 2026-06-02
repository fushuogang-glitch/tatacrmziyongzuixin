"""消耗明细模型 — 记录每次下店服务的扣费详情"""
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base


class PackageConsumption(Base):
    """套餐消耗明细 package_consumptions
    工单完成后自动写入，记录：谁去的、做了什么、扣多少、满意度
    """
    __tablename__ = "package_consumptions"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("service_packages.id"), index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("service_orders.id"), index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    consultant_id = Column(Integer, ForeignKey("consultants.id"))

    visit_number = Column(Integer)                   # 第几期
    service_name = Column(String(100))               # 做了什么
    service_category = Column(String(30))            # 分类
    deducted_amount = Column(Numeric(10, 2))         # 本次扣费
    duration_days = Column(Integer)                   # 服务天数
    appoint_date = Column(Date)                       # 下店日期
    store_name = Column(String(100))                  # 门店
    consultant_name = Column(String(50))              # 谁去的
    assistant_name = Column(String(50))               # 助理老师
    rating = Column(Integer)                          # 满意度 1-5
    rating_comment = Column(Text)                     # 评价内容
    summary = Column(Text)                            # 执案摘要

    created_at = Column(DateTime, server_default=func.now())
