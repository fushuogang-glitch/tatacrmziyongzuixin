# Agent IP 白名单校验
import ipaddress
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


def get_whitelist(db: Session) -> List[str]:
    """从数据库获取活跃的IP白名单"""
    rows = db.execute(text(
        'SELECT ip_address FROM agent_ip_whitelist WHERE is_active = true'
    )).fetchall()
    return [r[0] for r in rows]


def ip_in_whitelist(client_ip: str, whitelist: List[str]) -> bool:
    """
    检查客户端IP是否在白名单中。
    支持：精确匹配、CIDR网段匹配、IPv6前缀匹配。
    """
    if not client_ip:
        return False

    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in whitelist:
        try:
            # CIDR 网段匹配
            if '/' in entry:
                network = ipaddress.ip_network(entry, strict=False)
                if client_addr in network:
                    return True
            else:
                # 精确匹配
                if ipaddress.ip_address(entry) == client_addr:
                    return True
        except ValueError:
            continue

    return False


def get_client_ip(request) -> str:
    """从请求中提取真实客户端IP（支持反向代理）"""
    # 优先取 X-Forwarded-For（Nginx反代）
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        # 取第一个IP（最原始的客户端）
        return forwarded.split(',')[0].strip()
    
    # X-Real-IP
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    
    # 直连IP
    if request.client:
        return request.client.host
    
    return ''
