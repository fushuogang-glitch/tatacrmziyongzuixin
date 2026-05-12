# 学员相关
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Member
from schemas.api import MemberRegisterIn, MemberOut
from services.referral_service import bind_referral
from utils.auth import get_current_member, create_token, decode_token
from utils.helpers import ok, to_dict, gen_member_no, gen_referral_code
from fastapi.security import OAuth2PasswordBearer
from fastapi import Header


router = APIRouter(prefix="/api/members", tags=["members"])


def _member_out(m: Member) -> dict:
    data = to_dict(m, [
        "id", "name", "phone", "enterprise_name", "city", "role",
        "member_type", "member_no", "enroll_date", "expire_date",
        "referral_code", "referred_by", "status",
    ])
    data["face_bound"] = bool(m.face_token)
    return data


@router.post("/register")
def register(body: MemberRegisterIn, db: Session = Depends(get_db),
             authorization: str | None = Header(default=None)):
    """学员注册。允许两种入口：
    - 匿名注册（后台/运营）：直接按 phone 建档；
    - 小程序 guest token 注册：从 token.extra.openid 绑定。
    """
    openid = body.openid
    if not openid and authorization and authorization.lower().startswith("bearer "):
        try:
            payload = decode_token(authorization.split(" ", 1)[1])
            if payload.get("role") == "guest":
                openid = payload.get("openid") or payload.get("sub")
        except Exception:
            openid = None

    exist = db.query(Member).filter(Member.phone == body.phone).first()
    if exist:
        # 已存在：如果 openid 缺失则补齐
        if openid and not exist.openid:
            exist.openid = openid
            db.commit()
        token = create_token(subject=exist.id, role="member", extra={"openid": openid or ""})
        return ok({"token": token, "user": _member_out(exist)})

    m = Member(
        name=body.name,
        phone=body.phone,
        enterprise_name=body.enterprise_name,
        city=body.city,
        role=body.role,
        member_type=body.member_type or "trial",
        enroll_date=date.today(),
        status="active",
        openid=openid,
    )
    db.add(m)
    db.flush()

    # 分配学员编号 / 推荐码
    m.member_no = gen_member_no(db)
    m.referral_code = gen_referral_code()

    # 绑定推荐关系
    bind_referral(db, m, body.referral_code)

    db.commit()
    db.refresh(m)

    token = create_token(subject=m.id, role="member", extra={"openid": openid or ""})
    return ok({"token": token, "user": _member_out(m)})


@router.get("/me")
def me(current: Member = Depends(get_current_member)):
    return ok(_member_out(current))
