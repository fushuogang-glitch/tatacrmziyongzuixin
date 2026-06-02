"""储值管理模型 recharges + recharge_consumptions - 2026-06-02

业务模型：
  客户买年度套餐 ¥20万/6次 → 生成 1 条 recharges（充值记录·总次数6/已用0/剩余6）
  每次老师下店执案完成 → 生成 1 条 recharge_consumptions（消耗记录·-1次）
  联动：service_workorders/bookings 完结时自动扣
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean, Date, func
from database import Base


class Recharge(Base):
    """储值/充值记录表 recharges
    
    一笔签约 = 一条 recharges 记录（与 payments 配对，但独立追踪次数）
    """
    __tablename__ = "recharges"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)  # 客户
    consultant_id = Column(Integer, ForeignKey("consultants.id"), index=True)           # 归属老师
    branch_id = Column(Integer, ForeignKey("branches.id"), index=True)                  # 分公司
    payment_id = Column(Integer, ForeignKey("payments.id"), index=True)                 # 关联收款记录（可空）
    package_id = Column(Integer, ForeignKey("service_packages.id"), index=True)         # 关联套餐
    service_id = Column(Integer, ForeignKey("services.id"), index=True)                 # 关联服务项目
    
    # 充值核心字段
    title = Column(String(200), nullable=False)                # 充值名称（如"年度战略发展·6次"）
    total_amount = Column(Numeric(12, 2), nullable=False)      # 充值总金额（如 ¥200,000）
    total_count = Column(Integer, nullable=False, default=1)   # 总次数（如 6）
    used_count = Column(Integer, nullable=False, default=0)    # 已用次数
    remaining_count = Column(Integer, nullable=False, default=0)  # 剩余次数（= total - used，触发器维护）
    unit_price = Column(Numeric(12, 2))                        # 单次价（= total_amount / total_count）
    
    # 时效
    start_date = Column(Date)                                  # 生效日
    expire_date = Column(Date)                                 # 失效日（年度套餐到期）
    
    # 状态
    status = Column(String(20), default="active", index=True)  # active 进行中 / used_up 用完 / expired 过期 / refunded 退款
    
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RechargeConsumption(Base):
    """储值消耗记录表 recharge_consumptions
    
    每次下店执案完成 / 课程上完 / 服务交付 → 扣 1 次（或自定义次数）
    """
    __tablename__ = "recharge_consumptions"

    id = Column(Integer, primary_key=True, index=True)
    recharge_id = Column(Integer, ForeignKey("recharges.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    consultant_id = Column(Integer, ForeignKey("consultants.id"), index=True)  # 提供服务的老师
    branch_id = Column(Integer, ForeignKey("branches.id"), index=True)
    
    # 消耗核心
    consume_date = Column(Date, nullable=False, index=True)    # 消耗日期
    consume_count = Column(Integer, nullable=False, default=1) # 消耗次数（一般 1）
    consume_amount = Column(Numeric(12, 2))                    # 折算金额（= consume_count × unit_price）
    
    # 关联业务（哪一次下店、哪个工单、哪节课）
    booking_id = Column(Integer, ForeignKey("visit_bookings.id"), index=True)         # 预约/下店记录
    workorder_id = Column(Integer)                                              # 工单ID
    course_session_id = Column(Integer, ForeignKey("course_sessions.id"))       # 课程场次
    
    # 状态：是否已取消
    status = Column(String(20), default="confirmed")  # confirmed 已确认 / cancelled 已取消（取消时回退次数）
    
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("admin_users.id"))  # 谁录的
