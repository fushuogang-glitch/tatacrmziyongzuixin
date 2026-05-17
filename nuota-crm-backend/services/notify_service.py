# 企微/短信通知（占位）
from typing import Optional

import httpx
from loguru import logger

from config import settings


def send_wecom(text: str, mentioned_mobiles: Optional[list] = None) -> bool:
    """企微群机器人通知。未配置 webhook 时走日志。"""
    url = settings.WECOM_WEBHOOK
    if not url or url.startswith("CONFIG."):
        logger.info(f"[mock-wecom] {text}")
        return True
    payload = {
        "msgtype": "text",
        "text": {
            "content": text,
            "mentioned_mobile_list": mentioned_mobiles or [],
        },
    }
    try:
        r = httpx.post(url, json=payload, timeout=5)
        return r.status_code == 200
    except Exception as e:
        logger.warning(f"企微通知失败: {e}")
        return False


def notify_referral_reward(referrer_name: str, referrer_phone: str) -> None:
    """推荐权益到账通知。"""
    text = f"🎉 {referrer_name} 老师，您的推荐奖励已到账（下店权益×1），可在小程序「权益中心」查看。"
    send_wecom(text, mentioned_mobiles=[referrer_phone])


def notify_booking_confirmed(member_name: str, phone: str, consultant_name: str, date_str: str) -> None:
    """下店预约确认通知。"""
    text = f"✅ {member_name}，您的下店预约已确认：顾问 {consultant_name}，日期 {date_str}。"
    send_wecom(text, mentioned_mobiles=[phone])


def notify_booking_applied(member_name: str, phone: str, preferred_date: str,
                           city: str, duration: int) -> None:
    """新下店预约提交 → 通知管理员。"""
    text = (
        f"📩 新下店预约\n"
        f"学员：{member_name}（{phone[-4:]}）\n"
        f"期望日期：{preferred_date}\n"
        f"城市：{city or '未填'}\n"
        f"时长：{duration}天\n"
        f"请前往后台确认并分配老师。"
    )
    send_wecom(text)
