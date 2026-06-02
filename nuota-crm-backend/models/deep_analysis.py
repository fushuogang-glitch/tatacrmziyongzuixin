"""会员深度分析 + 老师人才模型分析 - 2026-06-02
塔才 Agent 负责分析·老师只录原始资料
同一套分析模型（四色性格+MBTI+八字+特殊习惯+综合方案）
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, func
from database import Base


class MemberDeepAnalysis(Base):
    """客户深度分析 member_deep_analysis"""
    __tablename__ = "member_deep_analysis"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, unique=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), index=True)

    # 老师录入的原始资料
    raw_text = Column(Text)              # 文字描述
    raw_images = Column(JSON)            # 图片URL数组 ["url1","url2"]

    # 塔才分析的结构化结果
    color_analysis = Column(JSON)        # 四色性格 {red,blue,yellow,green,traits,dominant}
    mbti = Column(JSON)                  # {type, dims:{energy,mind,nature,tactics,identity}, desc}
    bazi = Column(JSON)                  # {pillars,features,shensha,dayun,liunian}
    special_habits = Column(Text)        # 特殊习惯

    # 产出
    service_guide = Column(Text)         # 服务接待指导方案（客户专属）
    summary = Column(Text)               # 综合摘要

    status = Column(String(20), default="pending", index=True)  # pending/analyzed
    analyzed_by = Column(String(50))     # 塔才
    analyzed_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey("admin_users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ConsultantTalentAnalysis(Base):
    """老师人才模型分析 consultant_talent_analysis"""
    __tablename__ = "consultant_talent_analysis"

    id = Column(Integer, primary_key=True, index=True)
    consultant_id = Column(Integer, ForeignKey("consultants.id"), nullable=False, unique=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), index=True)

    raw_text = Column(Text)
    raw_images = Column(JSON)

    color_analysis = Column(JSON)
    mbti = Column(JSON)
    bazi = Column(JSON)
    special_habits = Column(Text)

    teaching_guide = Column(Text)        # 带教指导方案（老师专属）
    summary = Column(Text)
    matched_members = Column(JSON)       # 匹配客户名单 [{member_id,name,reason}]

    status = Column(String(20), default="pending", index=True)
    analyzed_by = Column(String(50))
    analyzed_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey("admin_users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
