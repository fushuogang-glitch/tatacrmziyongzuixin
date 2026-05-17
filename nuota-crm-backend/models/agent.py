# Agent API Key 模型
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import Base


class AgentApiKey(Base):
    """Agent API Key — 每个Agent一把钥匙"""
    __tablename__ = "agent_api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), unique=True, nullable=False, index=True)  # bafang / sanhe / baichuan ...
    agent_name = Column(String(100), nullable=False)                        # 八方 / 三和 / 百川
    api_key = Column(String(100), unique=True, nullable=False, index=True)  # sk-agent-xxx
    permission_level = Column(String(20), nullable=False, default="business")  # full / business / readonly
    allowed_paths = Column(JSON, nullable=True)       # 可选：精细化路径白名单
    blocked_paths = Column(JSON, nullable=True)       # 可选：路径黑名单
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AgentApiKey {self.agent_id}:{self.agent_name}>"
