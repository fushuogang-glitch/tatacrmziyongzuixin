# 企业 & 邀请码 API（小程序端）
import random
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Member, Enterprise, EnterpriseInvite
from utils.auth import get_current_member
from utils.helpers import ok, to_dict

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])

MAX_TEAM_SIZE = 10  # 每个企业最多10人


# ---------- 创建企业（需要推荐码） ----------
@router.post("/create")
def create_enterprise(body: dict = {}, db: Session = Depends(get_db),
                      me: Member = Depends(get_current_member)):
    # 如果已有企业，直接返回
    if me.enterprise_id:
        ent = db.query(Enterprise).filter(Enterprise.id == me.enterprise_id).first()
        if ent:
            return ok(to_dict(ent))
    # 必须有推荐码（朋友推荐码 or 塔塔老师邀请码）
    referral_code = body.get("referral_code", "").strip()
    if not referral_code:
        raise HTTPException(status_code=400, detail="创建企业需要推荐码（朋友推荐码或塔塔老师邀请码）")
    # 验证推荐码：1) 学员推荐码 2) 老师邀请码
    from models.booking import Consultant
    valid = False
    # 检查学员推荐码
    referrer = db.query(Member).filter(Member.referral_code == referral_code).first()
    if referrer:
        valid = True
    # 检查老师邀请码
    if not valid:
        try:
            from models.booking import ConsultantInviteCode
            teacher_code = db.query(ConsultantInviteCode).filter(
                ConsultantInviteCode.code == referral_code,
                ConsultantInviteCode.is_used == False,
            ).first()
            if teacher_code:
                valid = True
        except Exception:
            pass
    if not valid:
        raise HTTPException(status_code=400, detail="推荐码无效，请联系朋友或塔塔老师获取")
    # 创建企业
    ent_name = body.get("enterprise_name") or me.enterprise_name or f"{me.name}的企业"
    ent = Enterprise(
        name=ent_name,
        city=body.get("city") or me.city or "",
        contact_phone=me.phone,
        boss_member_id=me.id,
        status="active",
    )
    db.add(ent)
    db.flush()
    me.enterprise_id = ent.id
    me.role = "boss"
    if ent_name:
        me.enterprise_name = ent_name
    db.commit()
    db.refresh(ent)
    return ok(to_dict(ent))


# ---------- 查看我的企业 ----------
@router.get("/mine")
def my_enterprise(db: Session = Depends(get_db), me: Member = Depends(get_current_member)):
    if not me.enterprise_id:
        return ok(None)
    ent = db.query(Enterprise).filter(Enterprise.id == me.enterprise_id).first()
    if not ent:
        return ok(None)
    data = to_dict(ent)
    members = db.query(Member).filter(
        Member.enterprise_id == ent.id,
        Member.status == "active"
    ).all()
    data["team"] = [{"id": m.id, "name": m.name, "phone": m.phone, "role": m.role,
                     "member_tier": m.member_tier} for m in members]
    data["team_count"] = len(members)
    data["max_team_size"] = MAX_TEAM_SIZE
    return ok(data)


# ---------- 生成邀请码 ----------
@router.post("/invite")
def create_invite(
    body: dict = {},
    db: Session = Depends(get_db),
    me: Member = Depends(get_current_member),
):
    if not me.enterprise_id:
        raise HTTPException(status_code=400, detail="请先创建企业")
    if me.role != "boss":
        raise HTTPException(status_code=403, detail="仅老板可邀请成员")
    # 检查团队人数上限
    current_count = db.query(Member).filter(
        Member.enterprise_id == me.enterprise_id,
        Member.status == "active"
    ).count()
    if current_count >= MAX_TEAM_SIZE:
        raise HTTPException(status_code=400, detail=f"团队已满（最多{MAX_TEAM_SIZE}人）")
    role = body.get("role", "manager")
    max_uses = min(body.get("max_uses", 5), MAX_TEAM_SIZE - current_count)
    days = body.get("days", 7)
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    while db.query(EnterpriseInvite).filter(EnterpriseInvite.code == code).first():
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    invite = EnterpriseInvite(
        enterprise_id=me.enterprise_id,
        code=code,
        role=role,
        created_by=me.id,
        max_uses=max_uses,
        expires_at=datetime.now() + timedelta(days=days),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return ok({"code": invite.code, "role": role, "max_uses": max_uses,
               "expires_at": str(invite.expires_at), "id": invite.id})


# ---------- 验证邀请码（注册前调用） ----------
@router.get("/invite/verify")
def verify_invite(code: str, db: Session = Depends(get_db)):
    invite = db.query(EnterpriseInvite).filter(
        EnterpriseInvite.code == code.upper(),
        EnterpriseInvite.status == "active",
    ).first()
    if not invite:
        raise HTTPException(status_code=404, detail="邀请码无效")
    if invite.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="邀请码已过期")
    if invite.used_count >= invite.max_uses:
        raise HTTPException(status_code=400, detail="邀请码已用完")
    # 检查企业人数上限
    current_count = db.query(Member).filter(
        Member.enterprise_id == invite.enterprise_id,
        Member.status == "active"
    ).count()
    if current_count >= MAX_TEAM_SIZE:
        raise HTTPException(status_code=400, detail="该企业团队已满")
    ent = db.query(Enterprise).filter(Enterprise.id == invite.enterprise_id).first()
    return ok({
        "enterprise_name": ent.name if ent else "",
        "enterprise_id": invite.enterprise_id,
        "role": invite.role,
        "code": invite.code,
    })


# ---------- 使用邀请码加入企业 ----------
@router.post("/invite/join")
def join_enterprise(
    body: dict,
    db: Session = Depends(get_db),
    me: Member = Depends(get_current_member),
):
    code = body.get("code", "").upper()
    invite = db.query(EnterpriseInvite).filter(
        EnterpriseInvite.code == code,
        EnterpriseInvite.status == "active",
    ).first()
    if not invite:
        raise HTTPException(status_code=404, detail="邀请码无效")
    if invite.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="邀请码已过期")
    if invite.used_count >= invite.max_uses:
        raise HTTPException(status_code=400, detail="邀请码已用完")
    if me.enterprise_id and me.enterprise_id != invite.enterprise_id:
        raise HTTPException(status_code=400, detail="您已属于其他企业")
    # 检查企业人数上限
    current_count = db.query(Member).filter(
        Member.enterprise_id == invite.enterprise_id,
        Member.status == "active"
    ).count()
    if current_count >= MAX_TEAM_SIZE:
        raise HTTPException(status_code=400, detail=f"该企业团队已满（最多{MAX_TEAM_SIZE}人）")
    me.enterprise_id = invite.enterprise_id
    me.role = invite.role
    ent = db.query(Enterprise).filter(Enterprise.id == invite.enterprise_id).first()
    if ent:
        me.enterprise_name = ent.name
        me.city = ent.city or me.city
    invite.used_count += 1
    db.commit()
    return ok({"msg": f"已加入{ent.name if ent else '企业'}", "role": invite.role})


# ---------- 团队成员管理 ----------
@router.get("/team")
def team_list(db: Session = Depends(get_db), me: Member = Depends(get_current_member)):
    if not me.enterprise_id:
        return ok([])
    members = db.query(Member).filter(
        Member.enterprise_id == me.enterprise_id,
        Member.status == "active"
    ).all()
    return ok([{"id": m.id, "name": m.name, "phone": m.phone, "role": m.role,
                "member_tier": m.member_tier, "is_boss": m.id == me.id}
               for m in members])


@router.post("/team/remove")
def remove_member(
    body: dict,
    db: Session = Depends(get_db),
    me: Member = Depends(get_current_member),
):
    if me.role != "boss":
        raise HTTPException(status_code=403, detail="仅老板可移除成员")
    mid = body.get("member_id")
    if mid == me.id:
        raise HTTPException(status_code=400, detail="不能移除自己")
    m = db.query(Member).filter(Member.id == mid, Member.enterprise_id == me.enterprise_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="成员不存在")
    m.enterprise_id = None
    db.commit()
    return ok({"msg": f"已移除{m.name}"})


# ---------- 我的邀请码列表 ----------
@router.get("/invites")
def my_invites(db: Session = Depends(get_db), me: Member = Depends(get_current_member)):
    if not me.enterprise_id:
        return ok([])
    invites = db.query(EnterpriseInvite).filter(
        EnterpriseInvite.enterprise_id == me.enterprise_id
    ).order_by(EnterpriseInvite.id.desc()).limit(20).all()
    now = datetime.now()
    return ok([{
        "id": inv.id, "code": inv.code, "role": inv.role,
        "max_uses": inv.max_uses, "used_count": inv.used_count,
        "expires_at": str(inv.expires_at),
        "expired": inv.expires_at < now,
        "created_at": str(inv.created_at),
    } for inv in invites])
