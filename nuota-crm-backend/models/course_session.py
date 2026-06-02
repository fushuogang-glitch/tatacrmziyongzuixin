"""课程场次模型 — 课程开课管理+报名+签到+跟进"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Text, Boolean,
    ForeignKey, JSON
)
from sqlalchemy.sql import func
from database import Base


class CourseSession(Base):
    """课程场次 course_sessions
    一个Service(课程产品)可以开多期场次
    """
    __tablename__ = "course_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_no = Column(String(30), unique=True, index=True)  # CS-2026-0001
    service_id = Column(Integer, ForeignKey("services.id"), index=True, nullable=False)
    title = Column(String(200))                                # 第3期·三业运营实战课
    edition = Column(Integer, default=1)                       # 第几期
    city = Column(String(50))                                  # 开课城市
    venue = Column(String(200))                                # 场地地址
    start_date = Column(Date, nullable=False)                  # 开课日期
    end_date = Column(Date, nullable=False)                    # 结课日期
    duration_days = Column(Integer, default=3)                 # 课程天数
    capacity = Column(Integer, default=50)                     # 名额上限
    enrolled_count = Column(Integer, default=0)                # 已报名人数
    checkin_count = Column(Integer, default=0)                 # 已签到人数

    # 价格（独立于套餐，课程单独付费）
    normal_price = Column(Numeric(10, 2))                      # 正常价格
    trial_price = Column(Numeric(10, 2))                       # 试听价格

    # 状态
    status = Column(String(20), default="enrolling")           # enrolling/ongoing/ended/cancelled
    # enrolling=报名中, ongoing=进行中, ended=已结束(变灰), cancelled=已取消

    # 自动化标记
    survey_sent = Column(Boolean, default=False)               # T-20 调研表已发
    ticket_remind_sent = Column(Boolean, default=False)        # T-10 订票提醒已发
    notify_sent = Column(Boolean, default=False)               # T-5 通知已发

    # 课程介绍
    description = Column(Text)                                 # 课程介绍（富文本）
    cover_image = Column(String(255))                          # 封面图
    highlights = Column(Text)                                  # 课程亮点（JSON数组）
    target_audience = Column(Text)                              # 适合人群（JSON数组）

    # 课程回顾
    review_content = Column(Text)                              # 结课回顾
    review_images = Column(Text)                               # 回顾图片

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CourseEnrollment(Base):
    """课程报名记录 course_enrollments
    会员报名一个场次 → 付费 → 签到 → 课后跟进
    """
    __tablename__ = "course_enrollments_v2"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_no = Column(String(30), unique=True, index=True)  # CE-2026-0001
    session_id = Column(Integer, ForeignKey("course_sessions.id"), index=True, nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), index=True, nullable=False)
    consultant_id = Column(Integer, ForeignKey("consultants.id"))  # 归属老师
    service_id = Column(Integer, ForeignKey("services.id"))        # 冗余：课程产品

    # 付费信息
    price_type = Column(String(20), default="normal")          # normal/trial 正常价/试听价
    paid_amount = Column(Numeric(10, 2))                       # 实付金额
    payment_id = Column(Integer, ForeignKey("payments.id"))    # 关联收款记录
    pay_status = Column(String(20), default="pending")         # pending/paid/refunded

    # 状态流转: enrolled → paid → checked_in → completed → follow_up → closed
    status = Column(String(20), default="enrolled")

    # 签到记录
    checkin_days = Column(JSON, default=list)                  # [{"day":1,"time":"2026-06-15 08:30","face":true}, ...]
    checkin_total = Column(Integer, default=0)                 # 总签到天数

    # 课后跟进
    signed_deal = Column(Boolean, default=False)               # 是否课程期间签单
    deal_order_id = Column(Integer, ForeignKey("service_orders.id"))  # 签单的工单ID
    followup_count = Column(Integer, default=0)                # 跟进次数
    next_followup_date = Column(Date)                          # 下次跟进日期（三和用）
    last_followup_at = Column(DateTime)                        # 上次跟进时间
    followup_notes = Column(Text)                              # 跟进备注

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CourseCheckin(Base):
    """课程扫脸签到明细 course_checkins
    每次扫脸签到的详细记录（含人脸匹配分数）
    """
    __tablename__ = "course_checkins"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("course_sessions.id"), index=True)
    enrollment_id = Column(Integer, ForeignKey("course_enrollments_v2.id"), index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    day_number = Column(Integer)                               # 第几天
    checkin_time = Column(DateTime, server_default=func.now()) # 签到时间
    checkin_type = Column(String(20), default="face")          # face/manual/qrcode
    face_score = Column(Numeric(5, 2))                         # 人脸匹配分数
    photo_url = Column(String(255))                            # 签到照片

    created_at = Column(DateTime, server_default=func.now())


class CourseFollowup(Base):
    """课后跟进记录 course_followups
    课后对未成交客户的跟进记录（三和Agent驱动）
    """
    __tablename__ = "course_followups"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("course_enrollments_v2.id"), index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True)
    consultant_id = Column(Integer, ForeignKey("consultants.id"))
    followup_type = Column(String(20), default="system")       # system/manual/agent
    content = Column(Text)                                      # 跟进内容
    result = Column(String(20))                                 # interested/not_now/rejected/signed
    next_action = Column(Text)                                  # 下一步计划
    triggered_by = Column(String(30))                           # cron/agent_sanhe/manual

    created_at = Column(DateTime, server_default=func.now())
