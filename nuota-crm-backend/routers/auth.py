# 认证：微信登录 & 后台登录
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Member, AdminUser
from schemas.api import WxLoginIn, AdminLoginIn, TokenOut
from services.wx_service import code2session
from utils.auth import create_token, verify_password
from utils.helpers import ok, to_dict
from config import settings


router = APIRouter(prefix="/api/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.post("/wx-login")
def wx_login(body: WxLoginIn, db: Session = Depends(get_db)):
    """小程序登录：code -> openid -> member（如未注册返回 need_register=True）。"""
    sess = code2session(body.code)
    openid = sess.get("openid")
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录失败")

    member = db.query(Member).filter(Member.openid == openid).first()
    if not member:
        # 尚未注册：返回一个临时 token（role=guest），前端拿到 openid 走注册
        tmp = create_token(subject=openid, role="guest", extra={"openid": openid})
        return ok({
            "need_register": True,
            "openid": openid,
            "token": tmp,
        })

    # 被移除的员工禁止登录
    if member.status == "removed":
        return ok({
            "need_register": False,
            "blocked": True,
            "msg": "您的账号已被企业管理员移除，请联系管理员重新邀请",
        })

    token = create_token(subject=member.id, role="member", extra={"openid": openid})
    return ok({
        "need_register": False,
        "token": token,
        "user": to_dict(member, [
            "id", "name", "phone", "member_no", "member_type",
            "referral_code", "status", "enroll_date", "expire_date",
            "enterprise_name", "city", "role", "enterprise_id",
            "consultant_id", "member_tier", "gender", "birthday",
        ]),
    })


@admin_router.post("/login", response_model=None)
def admin_login(body: AdminLoginIn, db: Session = Depends(get_db)):
    """后台登录：用户名+密码。"""
    user = db.query(AdminUser).filter(AdminUser.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已停用")
    token = create_token(subject=user.id, role=user.role or "admin")
    return ok({
        "token": token,
        "role": user.role,
        "expires_in_days": settings.JWT_EXPIRE_DAYS,
        "user": {"id": user.id, "username": user.username, "real_name": user.real_name},
    })


@router.post("/debug-login")
async def debug_login(body: dict, db: Session = Depends(get_db)):
    """开发者工具调试专用，用member_id直接登录"""
    if settings.is_production:
        raise HTTPException(status_code=404, detail="接口不存在")
    member_id = body.get("member_id", 1)
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    token = create_token(subject=member.id, role="member", extra={"openid": member.openid or "debug"})
    return ok({
        "need_register": False,
        "token": token,
        "user": to_dict(member, [
            "id", "name", "phone", "member_no", "member_type",
            "referral_code", "status", "enroll_date", "expire_date",
            "enterprise_name", "city", "role", "enterprise_id",
            "consultant_id", "member_tier", "gender", "birthday",
        ]),
    })
