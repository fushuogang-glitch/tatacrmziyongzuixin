# 专案服务模型（年费制 · 老师下店服务）
from sqlalchemy import (
    Column, Integer, String, Text, Date, Numeric, DateTime, ForeignKey, Boolean
)
from sqlalchemy.sql import func

from database import Base


class Service(Base):
    """专案服务定义 services
    塔塔老师提供的标准化专案服务（如品项搭建/团队培训/品牌升级等）
    """
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)                # 服务名称
    code = Column(String(30), unique=True, index=True)        # 服务编码 SV-001
    category = Column(String(30))                             # 发展/增长/课程/供应商服务
    brand = Column(String(50), default="塔塔")               # 塔塔/九木/九凤
    description = Column(Text)
    service_mode = Column(String(20), default="annual")       # annual=1年制 / times=按次制
    total_times = Column(Integer, default=5)                  # 按次制：包含次数（5次等）
    duration_days = Column(Integer, default=1)                # 单次服务天数(1-5天)
    price = Column(Numeric(10, 2))                            # 正常价格
    trial_price = Column(Numeric(10, 2))                      # 试听价格（课程类专用）
    annual_price = Column(Numeric(10, 2))                     # 年度套餐价格
    cover_image = Column(String(255))                         # 封面图
    status = Column(String(20), default="active")             # active/offline

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ServicePackage(Base):
    """会员专案年费套餐 service_packages
    会员购买的年度专案服务包（包含N次专案服务额度）
    """
    __tablename__ = "service_packages"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True, nullable=False)
    package_no = Column(String(30), unique=True, index=True)   # PKG-2026-0001
    total_times = Column(Integer, default=0)                   # 包含次数
    used_times = Column(Integer, default=0)                    # 已使用次数
    amount = Column(Numeric(10, 2))                            # 套餐金额
    per_time_fee = Column(Numeric(10, 2))                      # 每次扣费额 = amount / total_times
    pay_type = Column(String(20), default="annual")             # annual/single
    start_date = Column(Date)                                  # 生效日期
    expire_date = Column(Date)                                 # 到期日期
    status = Column(String(20), default="active")              # active/expired/frozen
    remark = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ServiceOrder(Base):
    """专案服务工单 service_orders
    会员预约一次专案服务 → 生成工单 → 老师执案 → 完成 → 满意度
    """
    __tablename__ = "service_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(30), unique=True, index=True)     # SO-2026-0001
    member_id = Column(Integer, ForeignKey("members.id"), index=True, nullable=True)  # 可空（排期自动创建时可无会员）
    service_id = Column(Integer, ForeignKey("services.id"), index=True)
    package_id = Column(Integer, ForeignKey("service_packages.id"))  # 关联的年费套餐
    consultant_id = Column(Integer, ForeignKey("consultants.id"))    # 主案老师
    assistant_id = Column(Integer, ForeignKey("consultants.id"))      # 助理老师（可空）
    store_name = Column(String(100))                           # 服务门店
    store_address = Column(Text)
    visit_number = Column(Integer, default=1)                   # 第几期下店
    appoint_date = Column(Date)                                # 预约日期
    appoint_time = Column(String(10))                          # 预约时段 09:00-12:00
    status = Column(String(20), default="pending")             # pending/confirmed/in_progress/completed/cancelled
    workflow_stage = Column(String(30))                        # 当前阶段：诊断/方案/执行/复盘
    workflow_progress = Column(Integer, default=0)             # 进度 0-100
    rating = Column(Integer)                                   # 满意度 1-5
    rating_comment = Column(Text)
    rated_at = Column(DateTime)
    remark = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ServiceWorkLog(Base):
    """工单执行日志 service_work_logs
    老师在执案过程中填写的工作记录
    """
    __tablename__ = "service_work_logs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("service_orders.id"), index=True, nullable=False)
    stage = Column(String(30))                                 # 诊断/方案/执行/复盘/接单/执案准备/执案报告
    content = Column(Text)
    images = Column(Text)                                      # 图片URL JSON数组
    consultant_id = Column(Integer, ForeignKey("consultants.id"))
    day_number = Column(Integer)                               # 第几天（Day1/Day2/Day3）
    findings = Column(Text)                                    # 发现的问题
    decisions = Column(Text)                                   # 达成的共识/决策
    next_actions = Column(Text)                                # 下一步计划
    log_type = Column(String(20), default="note")              # note/daily/report/prepare/system

    created_at = Column(DateTime, server_default=func.now())


class UserAgreement(Base):
    """用户协议签约审计表 user_agreements
    每次签约生成一条记录（含 IP/UA/时间/版本/hash）
    """
    __tablename__ = "user_agreements"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True, nullable=False)
    agreement_version = Column(String(20), nullable=False)     # v1.0
    agreement_hash = Column(String(64))                        # 协议内容 SHA256
    signed_at = Column(DateTime, server_default=func.now())
    client_ip = Column(String(45))
    client_ua = Column(Text)
    signature = Column(Text)                                   # 手写签名 base64（可选）
    is_valid = Column(Boolean, default=True)                   # 协议是否仍有效
