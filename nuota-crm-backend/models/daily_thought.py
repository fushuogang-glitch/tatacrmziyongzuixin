"""每日一念 / 会员文化画像."""
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.sql import func

from database import Base


class MemberDailyProfile(Base):
    """会员每日一念资料，保存生辰、月度解读及老师补充画像。"""

    __tablename__ = "member_daily_profiles"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), unique=True, index=True, nullable=False)
    birth_date = Column(Date)
    birth_time = Column(String(20))
    bazi_text = Column(String(120))
    profile_type = Column(String(20), default="customer")  # customer/employee/partner/boss
    monthly_fortune_month = Column(String(7))  # YYYY-MM
    monthly_fortune = Column(Text)
    current_liuyue = Column(String(30))  # 当前流月，如：丙午月
    good_events_analysis = Column(Text)  # 小程序展示：好事/机会分析
    caution_notes = Column(Text)  # 小程序展示：注意事项
    auspicious_keyword = Column(String(50))
    color_personality = Column(String(100))
    mbti = Column(String(20))
    bazi_analysis = Column(Text)  # 老师/命理师输入的专业八字测算内容
    teacher_notes = Column(Text)
    # 塔才 Agent 生成（四色×MBTI×八字 → 评语+沟通+经营+服务）
    taicai_comment = Column(Text)
    taicai_communication = Column(Text)
    taicai_business_tip = Column(Text)
    taicai_service_tip = Column(Text)
    taicai_generated_at = Column(DateTime)
    updated_by = Column(Integer, ForeignKey("admin_users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DailyThoughtRecord(Base):
    """每日展示记录，保证同一会员同一天看到同一组内容。"""

    __tablename__ = "daily_thought_records"
    __table_args__ = (
        UniqueConstraint("member_id", "record_date", name="uq_daily_thought_member_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True, nullable=False)
    record_date = Column(Date, index=True, nullable=False)
    word = Column(String(30), nullable=False)
    hexagram = Column(String(60))
    meaning = Column(Text)
    almanac_good = Column(String(200))
    almanac_avoid = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())
