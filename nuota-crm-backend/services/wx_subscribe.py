"""微信订阅消息推送服务"""
import requests
import time
import logging

logger = logging.getLogger(__name__)

_token_cache = {"token": "", "expires": 0}


def get_access_token():
    """获取并缓存 access_token"""
    import os
    now = time.time()
    if _token_cache["token"] and _token_cache["expires"] > now + 60:
        return _token_cache["token"]

    appid = os.getenv("WX_APPID", "wxf6a6e4ce11b11dd8")
    secret = os.getenv("WX_SECRET", "3f377bd512b59f5a0266575cf8910560")
    r = requests.get(
        f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}",
        timeout=10,
    )
    data = r.json()
    token = data.get("access_token", "")
    if token:
        _token_cache["token"] = token
        _token_cache["expires"] = now + data.get("expires_in", 7200)
    return token


# 模板ID
TMPL_SERVICE_PROGRESS = "7xpNpfWLy2mJglIOMDm33b8zh70yvkcZNrD8ZzFDpLc"
TMPL_SERVICE_REPORT = "LG6ccbuEK6AWYq7f_KSFOvXk_bFbKc6nfoo4yLRJPyE"
TMPL_PAYMENT_SUCCESS = "mfrAmmuLINMEJ0f9ZzZbF4b7h9yunwPZ4T9GC9hj3LQ"
TMPL_REVIEW_REMIND = "ZXRO3dZ4erB0toB2588XegppqitD8TEV2GuMjNTl2rs"


def send_subscribe_msg(openid: str, template_id: str, data: dict, page: str = ""):
    """发送订阅消息
    data 格式: {"thing6": {"value": "xxx"}, "thing3": {"value": "yyy"}, ...}
    """
    token = get_access_token()
    if not token:
        logger.error("获取 access_token 失败")
        return False

    payload = {
        "touser": openid,
        "template_id": template_id,
        "data": data,
    }
    if page:
        payload["page"] = page
    # miniprogram_state: formal=正式版 trial=体验版 developer=开发版
    payload["miniprogram_state"] = "trial"

    r = requests.post(
        f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}",
        json=payload,
        timeout=10,
    )
    result = r.json()
    if result.get("errcode") == 0:
        logger.info(f"订阅消息发送成功: openid={openid}, tmpl={template_id}")
        return True
    else:
        logger.warning(f"订阅消息发送失败: {result}")
        return False


def notify_service_progress(openid: str, service_title: str, progress: str, consultant_name: str, service_time: str, page: str = ""):
    """服务进度通知"""
    return send_subscribe_msg(openid, TMPL_SERVICE_PROGRESS, {
        "thing6": {"value": service_title[:20]},
        "thing3": {"value": progress[:20]},
        "short_thing7": {"value": consultant_name[:4]},
        "time4": {"value": service_time},
    }, page)


def notify_service_report(openid: str, service_name: str, content: str, tip: str, consultant_name: str, notify_time: str, page: str = ""):
    """服务汇报通知"""
    return send_subscribe_msg(openid, TMPL_SERVICE_REPORT, {
        "thing1": {"value": service_name[:20]},
        "thing2": {"value": content[:20]},
        "thing3": {"value": tip[:20]},
        "thing4": {"value": consultant_name[:20]},
        "time5": {"value": notify_time},
    }, page)


def notify_payment_success(openid: str, service_name: str, product_detail: str, amount: str, pay_time: str, contact: str, page: str = ""):
    """购买成功通知"""
    return send_subscribe_msg(openid, TMPL_PAYMENT_SUCCESS, {
        "thing1": {"value": service_name[:20]},
        "thing7": {"value": product_detail[:20]},
        "amount5": {"value": amount},
        "date6": {"value": pay_time},
        "thing12": {"value": contact[:20]},
    }, page)
