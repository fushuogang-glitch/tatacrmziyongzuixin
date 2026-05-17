# 客户跟进记录模型
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class FollowUp(Base):
    """跟进记录表 follow_ups"""
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), index=True, nullable=False)
    admin_id = Column(Integer, ForeignKey("admin_users.id"), index=True)
    admin_name = Column(String(50))                            # 冗余字段，避免join
    status = Column(String(20), default="following")           # intention/following/closed/lost/silent
    content = Column(Text, nullable=False)                     # 跟进内容
    follow_type = Column(String(20), default="note")           # note/call/visit/wechat
    next_follow_date = Column(DateTime)                        # 下次跟进时间
    created_at = Column(DateTime, server_default=func.now())
