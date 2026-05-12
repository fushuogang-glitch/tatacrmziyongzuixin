# 微信登录服务（占位）
# 生产：用 wx.login 的 code + appid/secret 调用 code2session 换 openid/session_key
import hashlib
from typing import Dict

import httpx
from loguru import logger

from config import settings


def code2session(code: str) -> Dict[str, str]:
    """用 code 换 openid。未配置 WX_APPID 时使用 mock（按 code 生成稳定 openid）。"""
    if settings.WX_APPID.startswith("CONFIG.") or not code:
        digest = hashlib.sha256((code or "mock").encode()).hexdigest()[:28]
        return {"openid": f"mock_oid_{digest}", "session_key": "mock_sk"}

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WX_APPID,
        "secret": settings.WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        r = httpx.get(url, params=params, timeout=5)
        data = r.json()
        if "openid" not in data:
            logger.warning(f"wx code2session 返回异常: {data}")
            return {"openid": "", "session_key": ""}
        return {"openid": data["openid"], "session_key": data.get("session_key", "")}
    except Exception as e:
        logger.warning(f"wx code2session 失败: {e}")
        return {"openid": "", "session_key": ""}
