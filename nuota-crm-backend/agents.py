# Agent 管理路由 + 补缺接口 + Webhook 事件总线
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models.agent import AgentApiKey
from utils.auth import get_current_admin
from utils.agent_auth import generate_api_key

router = APIRouter(prefix="/admin/agents", tags=["Agent管理"])


# ═══ Schema ═══
class AgentKeyCreate(BaseModel):
    agent_id: str
    agent_name: str
    permission_level: str = "business"  # full / business / readonly
    notes: Optional[str] = None

class AgentKeyOut(BaseModel):
    id: int
    agent_id: str
    agent_name: str
    api_key: str
    permission_level: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ═══ CRUD ═══
@router.get("", response_model=List[AgentKeyOut])
def list_agent_keys(admin=Depends(get_current_admin), db: DBSession = Depends(get_db)):
    """列出所有 Agent API Key"""
    return db.query(AgentApiKey).order_by(AgentApiKey.id).all()


@router.post("", response_model=AgentKeyOut)
def create_agent_key(body: AgentKeyCreate, admin=Depends(get_current_admin), db: DBSession = Depends(get_db)):
    """创建 Agent API Key"""
    exists = db.query(AgentApiKey).filter(AgentApiKey.agent_id == body.agent_id).first()
    if exists:
        raise HTTPException(400, f"Agent [{body.agent_id}] 已存在")

    key = AgentApiKey(
        agent_id=body.agent_id,
        agent_name=body.agent_name,
        api_key=generate_api_key(body.agent_id),
        permission_level=body.permission_level,
        notes=body.notes,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


@router.put("/{agent_id}/regenerate", response_model=AgentKeyOut)
def regenerate_key(agent_id: str, admin=Depends(get_current_admin), db: DBSession = Depends(get_db)):
    """重新生成 API Key"""
    key = db.query(AgentApiKey).filter(AgentApiKey.agent_id == agent_id).first()
    if not key:
        raise HTTPException(404, "Agent不存在")
    key.api_key = generate_api_key(agent_id)
    db.commit()
    db.refresh(key)
    return key


@router.put("/{agent_id}/toggle")
def toggle_agent(agent_id: str, admin=Depends(get_current_admin), db: DBSession = Depends(get_db)):
    """启用/禁用 Agent"""
    key = db.query(AgentApiKey).filter(AgentApiKey.agent_id == agent_id).first()
    if not key:
        raise HTTPException(404, "Agent不存在")
    key.is_active = not key.is_active
    db.commit()
    return {"agent_id": agent_id, "is_active": key.is_active}


@router.delete("/{agent_id}")
def delete_agent(agent_id: str, admin=Depends(get_current_admin), db: DBSession = Depends(get_db)):
    """删除 Agent Key"""
    key = db.query(AgentApiKey).filter(AgentApiKey.agent_id == agent_id).first()
    if not key:
        raise HTTPException(404, "Agent不存在")
    db.delete(key)
    db.commit()
    return {"ok": True}
