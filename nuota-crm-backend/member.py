# 学员/缴费模型
from sqlalchemy import (
    Column, Integer, String, Text, Date, Numeric, DateTime, ForeignKey, Boolean
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
    store_count = Column(Integer, default=1)                   # 门店数量 1-100
    store_type = Column(String(30))                            # 门店性质
    pre_annual_revenue = Column(Numeric(12, 2))                # 合作前年产值(元)
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

    # 企业关联
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), index=True)

    # 会员分级（年度消费累计）
    member_tier = Column(String(20), default="primary")        # primary/junior/senior/college/teacher
    annual_spending = Column(Numeric(12, 2), default=0)        # 年度累计消费
    spending_year = Column(Integer)                            # 统计年份

    # 归属老师
    gender = Column(String(10), default="female")               # male/female 性别
    birthday = Column(Date)                                       # 生日（月-日）用于生日营销
    consultant_id = Column(Integer, ForeignKey("consultants.id"), index=True)  # 归属老师ID

    # 历史补录（后台手动录入的历史数据）
    history_course_count = Column(Integer, default=0)           # 历史课程次数
    history_service_count = Column(Integer, default=0)          # 历史专案服务次数
    history_referral_count = Column(Integer, default=0)         # 历史推荐人数

    # 人脸认证状态
    face_bound = Column(Boolean, default=False)                # 是否已绑定人脸
    face_bound_at = Column(DateTime)                           # 人脸绑定时间

    # Agent 标签 & 备注
    tags = Column(String(500))                                  # 标签（逗号分隔）
    notes = Column(Text)                                        # 备注

    # 协议签约状态
    agreement_signed = Column(Boolean, default=False)
    agreement_version = Column(String(20))
    agreement_signed_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Payment(Base):
    """缴费记录表 payments"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    consultant_id = Column(Integer, ForeignKey("consultants.id"), index=True)  # 归属老师
    amount = Column(Numeric(10, 2))                            # 付款金额
    debt_amount = Column(Numeric(10, 2), default=0)            # 欠款金额
    pay_mode = Column(String(20), default="full")              # full/installment 全款/分期
    pay_method = Column(String(20))                            # company_account/private_account/wecom/wechat_proxy 对公/私户/企微/微信代收
    pay_type = Column(String(20))                              # trial/annual/single
    pay_status = Column(String(20), default="pending")         # pending/paid/partial/refunded
    package_id = Column(Integer, ForeignKey("service_packages.id"), index=True)  # 关联套餐
    service_id = Column(Integer, ForeignKey("services.id"))                       # 合作项目
    pay_time = Column(DateTime)
    due_date = Column(Date)                                    # 补款截止日期
    due_notified = Column(Boolean, default=False)              # 已发提醒标记
    remark = Column(Text)
    # 百川对账
    verified = Column(Boolean, default=False)                   # 对账确认
    verify_notes = Column(Text)                                 # 对账备注
    created_at = Column(DateTime, server_default=func.now())
