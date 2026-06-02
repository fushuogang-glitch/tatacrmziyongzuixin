# Agent 认证 & 权限中间件
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models.agent import AgentApiKey


# ═══ 权限规则 ═══
# full:     全部接口
# business: 业务接口（不含财务金额详情、操作日志）
# readonly: 只读接口（GET only）

PERMISSION_BLOCKS = {
    "business": [
        "/admin/payments",       # 财务收款（business不能直接看）
        "/admin/export/payments",
        "/admin/operation-logs",
    ],
    "readonly": [
        # readonly 只能GET，POST/PUT/DELETE 在下面拦截
    ],
}

# Agent专属可访问路径（覆盖block规则）
AGENT_OVERRIDES = {
    "baichuan": {
        # 百川是财务负责人：payments只读 + 采购管理全权限 + 储值全权限
        "allow": ["/admin/payments", "/admin/export/payments"],
        "methods": ["GET"],
        # 采购/储值：百川全权限（增删改查）
        "allow_write": ["/admin/purchases", "/admin/recharges"],
        "write_methods": ["GET", "POST", "PUT", "DELETE"],
    },
    "siku": {
        # 司库可以看日志
        "allow": ["/admin/operation-logs"],
        "methods": ["GET"],
    },
    "taicai": {
        # 塔才：深度分析读写（拉待分析+回写结果）
        "allow_write": ["/agent/deep-analysis"],
        "write_methods": ["GET", "POST", "PUT"],
    },
    "sanhe": {
        # 三和：客户管理+缴费只读（用于分析续费/补款）
        "allow": ["/agent/members", "/agent/finance/payments", "/agent/services", "/agent/workorders"],
        "methods": ["GET"],
    },
}


def generate_api_key(agent_id: str) -> str:
    """生成 Agent API Key"""
    random_part = secrets.token_hex(16)
    return f"sk-agent-{agent_id}-{random_part}"


class AgentAuth:
    """Agent身份对象，注入到路由里"""
    def __init__(self, agent_id: str, agent_name: str, permission_level: str, key_obj: AgentApiKey):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.permission_level = permission_level
        self.key_obj = key_obj

    @property
    def is_full(self) -> bool:
        return self.permission_level == "full"

    @property
    def is_readonly(self) -> bool:
        return self.permission_level == "readonly"


def get_agent_auth(
    request: Request,
    db: DBSession = Depends(get_db),
) -> Optional[AgentAuth]:
    """
    从请求头提取Agent身份。
    如果没有 X-Api-Key 头，返回 None（普通管理员请求）。
    如果有但无效，抛401。
    """
    api_key = request.headers.get("X-Api-Key") or request.headers.get("x-api-key")
    if not api_key:
        return None

    key_obj = db.query(AgentApiKey).filter(
        AgentApiKey.api_key == api_key,
        AgentApiKey.is_active == True,
    ).first()

    if not key_obj:
        raise HTTPException(status_code=401, detail="无效的 Agent API Key")

    # 更新最后使用时间
    key_obj.last_used_at = datetime.utcnow()
    db.commit()

    return AgentAuth(
        agent_id=key_obj.agent_id,
        agent_name=key_obj.agent_name,
        permission_level=key_obj.permission_level,
        key_obj=key_obj,
    )


def check_agent_permission(request: Request, agent: Optional[AgentAuth]):
    """
    检查Agent权限。在需要鉴权的路由里调用。
    - full: 全部通过
    - readonly: 只能GET
    - business: 不能访问财务/日志（除非有override）
    """
    if agent is None:
        return  # 普通管理员，不限制

    path = request.url.path
    method = request.method.upper()

    # 【优先】override 可写路径：放行（在 readonly 拦截之前）
    _ov = AGENT_OVERRIDES.get(agent.agent_id)
    if _ov:
        for _wp in _ov.get("allow_write", []):
            if path.startswith(_wp):
                _wm = _ov.get("write_methods", ["GET", "POST", "PUT", "DELETE"])
                if method in _wm:
                    return
                raise HTTPException(status_code=403, detail=f"Agent [{agent.agent_name}] 不允许 {method} {path}")

    # readonly 只能 GET
    if agent.permission_level == "readonly" and method != "GET":
        raise HTTPException(status_code=403, detail=f"Agent [{agent.agent_name}] 只有只读权限")

    # full 全部通过
    if agent.permission_level == "full":
        return

    # 检查 override
    override = AGENT_OVERRIDES.get(agent.agent_id)
    if override:
        # 1) allow_write：可写路径（增删改查全开）
        for wpath in override.get("allow_write", []):
            if path.startswith(wpath):
                wmethods = override.get("write_methods", ["GET", "POST", "PUT", "DELETE"])
                if method in wmethods:
                    return
                else:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Agent [{agent.agent_name}] 不允许 {method} {path}"
                    )
        # 2) allow：只读路径
        for allowed_path in override.get("allow", []):
            if path.startswith(allowed_path):
                allowed_methods = override.get("methods", ["GET", "POST", "PUT", "DELETE"])
                if method in allowed_methods:
                    return
                else:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Agent [{agent.agent_name}] 不允许 {method} {path}"
                    )

    # 检查 block 规则
    blocks = PERMISSION_BLOCKS.get(agent.permission_level, [])
    for blocked in blocks:
        if path.startswith(blocked):
            raise HTTPException(
                status_code=403,
                detail=f"Agent [{agent.agent_name}] 无权访问 {path}"
            )
