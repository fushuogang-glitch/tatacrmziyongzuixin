# 客户管理面板（卡片视图）— 复用 members 表，按门店/客户维度聚合
# 含：电话权限授权体系（限时7天，销售归属/管理员/超管可批）
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import get_db
from models import Member, Consultant, ServiceOrder
from utils.auth import get_current_admin_or_consultant, CurrentUser
from utils.helpers import ok

router = APIRouter(prefix="/admin/customers", tags=["customers"])


# ───────────────────────── 工具 ─────────────────────────
def _mask_phone(phone: str) -> str:
    if not phone:
        return ""
    p = str(phone)
    if len(p) >= 11:
        return p[:3] + "****" + p[-4:]
    if len(p) > 4:
        return p[:2] + "****"
    return "****"


def _active_grant_consultant_ids(db: Session, member_id: int) -> set:
    """返回对该客户当前有效授权的老师 id 集合"""
    rows = db.execute(text(
        "SELECT consultant_id FROM customer_phone_grants "
        "WHERE member_id=:mid AND status='approved' "
        "AND (expire_at IS NULL OR expire_at > now())"
    ), {"mid": member_id}).fetchall()
    return {r[0] for r in rows}


def _can_see_phone(db: Session, cur: CurrentUser, m: Member) -> bool:
    """管理员/超管全看；销售归属老师本人看；已获授权老师看；其余打码"""
    if cur.is_admin:
        return True
    if cur.is_consultant:
        if m.consultant_id and m.consultant_id == cur.consultant_id:
            return True
        if cur.consultant_id in _active_grant_consultant_ids(db, m.id):
            return True
    return False


def _service_done(db: Session, member_id: int) -> int:
    return db.query(func.count(ServiceOrder.id)).filter(
        ServiceOrder.member_id == member_id,
        ServiceOrder.status == "completed",
    ).scalar() or 0


# ───────────────────────── 列表 ─────────────────────────
@router.get("")
def list_customers(
    q: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    store_type: Optional[str] = None,
    consultant_id: Optional[int] = None,
    group_by: Optional[str] = Query(None, description="consultant/city/none"),
    page: int = Query(1, ge=1),
    size: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    cur: CurrentUser = Depends(get_current_admin_or_consultant),
):
    query = db.query(Member)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Member.name.ilike(like)) | (Member.phone.ilike(like)) |
            (Member.enterprise_name.ilike(like)) | (Member.address.ilike(like))
        )
    if city:
        query = query.filter(Member.city == city)
    if district:
        query = query.filter(Member.district == district)
    if store_type:
        query = query.filter(Member.store_type == store_type)
    if consultant_id:
        query = query.filter(Member.consultant_id == consultant_id)

    total = query.count()
    rows = query.order_by(Member.id.desc()).offset((page - 1) * size).limit(size).all()

    cids = list({m.consultant_id for m in rows if m.consultant_id})
    cmap = {}
    if cids:
        for c in db.query(Consultant).filter(Consultant.id.in_(cids)).all():
            cmap[c.id] = c.name or ""

    items = []
    for m in rows:
        done = _service_done(db, m.id)
        history_s = getattr(m, "history_service_count", 0) or 0
        can_phone = _can_see_phone(db, cur, m)
        is_owner = bool(cur.is_consultant and m.consultant_id == cur.consultant_id)
        items.append({
            "id": m.id,
            "name": m.name,
            "phone": m.phone if can_phone else _mask_phone(m.phone),
            "phone_masked": not can_phone,
            "is_owner": is_owner,
            "can_grant": cur.is_admin or is_owner,   # 谁可以审批授权
            "enterprise_name": m.enterprise_name or "",
            "address": getattr(m, "address", "") or "",
            "city": m.city or "",
            "district": getattr(m, "district", "") or "",
            "store_type": m.store_type or "",
            "store_count": m.store_count or 0,
            "cooperation": getattr(m, "cooperation", "") or "",
            "service_count": done + history_s,
            "service_done": done,
            "service_history": history_s,
            "consultant_id": m.consultant_id,
            "consultant_name": cmap.get(m.consultant_id, "") if m.consultant_id else "",
            "member_tier": m.member_tier or "",
            "member_type": m.member_type or "",
            "status": m.status or "active",
            "tags": m.tags or "",
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    # 分组
    grouped = None
    if group_by in ("consultant", "city"):
        buckets: dict = {}
        for it in items:
            if group_by == "consultant":
                key = it["consultant_name"] or "未分配"
            else:
                key = it["city"] or "未填写"
            buckets.setdefault(key, []).append(it)
        grouped = [{"group": k, "count": len(v), "items": v} for k, v in buckets.items()]
        grouped.sort(key=lambda x: -x["count"])

    return ok({"total": total, "page": page, "size": size, "items": items, "grouped": grouped})


@router.get("/filters")
def customer_filters(
    db: Session = Depends(get_db),
    cur: CurrentUser = Depends(get_current_admin_or_consultant),
):
    cities = [r[0] for r in db.query(Member.city).filter(Member.city.isnot(None)).distinct().all() if r[0]]
    districts = [r[0] for r in db.query(Member.district).filter(Member.district.isnot(None)).distinct().all() if r[0]]
    store_types = [r[0] for r in db.query(Member.store_type).filter(Member.store_type.isnot(None)).distinct().all() if r[0]]
    consultants = [{"id": c.id, "name": c.name} for c in db.query(Consultant).order_by(Consultant.id).all()]
    return ok({"cities": cities, "districts": districts, "store_types": store_types, "consultants": consultants})


@router.get("/stats")
def customer_stats(
    db: Session = Depends(get_db),
    cur: CurrentUser = Depends(get_current_admin_or_consultant),
):
    total = db.query(func.count(Member.id)).scalar() or 0
    city_cnt = db.query(func.count(func.distinct(Member.city))).filter(Member.city.isnot(None)).scalar() or 0
    store_sum = db.query(func.coalesce(func.sum(Member.store_count), 0)).scalar() or 0
    active = db.query(func.count(Member.id)).filter(Member.status == "active").scalar() or 0
    return ok({"total_customers": total, "total_cities": city_cnt,
               "total_stores": int(store_sum), "active_customers": active})


# ───────────────────────── 新增 / 编辑 ─────────────────────────
class CustomerIn(BaseModel):
    name: str
    phone: str
    enterprise_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    store_type: Optional[str] = None
    store_count: Optional[int] = None
    cooperation: Optional[str] = None
    consultant_id: Optional[int] = None
    member_type: Optional[str] = None
    status: Optional[str] = None


def _require_admin(cur: CurrentUser):
    if not cur.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可编辑客户档案")


@router.post("")
def create_customer(body: CustomerIn, db: Session = Depends(get_db),
                    cur: CurrentUser = Depends(get_current_admin_or_consultant)):
    _require_admin(cur)
    if db.query(Member).filter(Member.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="该电话已存在客户")
    m = Member(**body.model_dump(exclude_unset=True))
    if not m.status:
        m.status = "active"
    db.add(m)
    db.commit()
    db.refresh(m)
    return ok({"id": m.id})


@router.put("/{mid}")
def update_customer(mid: int, body: CustomerIn, db: Session = Depends(get_db),
                    cur: CurrentUser = Depends(get_current_admin_or_consultant)):
    _require_admin(cur)
    m = db.query(Member).filter(Member.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="客户不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    return ok({"id": m.id})


# ───────────────────────── 电话授权 ─────────────────────────
class GrantApplyIn(BaseModel):
    member_id: int
    reason: Optional[str] = None


@router.post("/phone-grant/apply")
def apply_phone_grant(body: GrantApplyIn, db: Session = Depends(get_db),
                      cur: CurrentUser = Depends(get_current_admin_or_consultant)):
    """非归属老师申请查看某客户电话"""
    if not cur.is_consultant:
        raise HTTPException(status_code=400, detail="仅老师需要申请")
    m = db.query(Member).filter(Member.id == body.member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="客户不存在")
    if m.consultant_id == cur.consultant_id:
        raise HTTPException(status_code=400, detail="您是该客户的销售归属，无需申请")
    # 已有有效授权
    if cur.consultant_id in _active_grant_consultant_ids(db, m.id):
        return ok({"status": "approved", "msg": "已有有效授权"})
    # 已有 pending
    exist = db.execute(text(
        "SELECT id FROM customer_phone_grants WHERE member_id=:mid AND consultant_id=:cid AND status='pending'"
    ), {"mid": m.id, "cid": cur.consultant_id}).first()
    if exist:
        return ok({"status": "pending", "msg": "申请已提交，等待审批"})
    db.execute(text(
        "INSERT INTO customer_phone_grants(member_id,consultant_id,status,reason,created_at,updated_at) "
        "VALUES(:mid,:cid,'pending',:reason,now(),now())"
    ), {"mid": m.id, "cid": cur.consultant_id, "reason": body.reason or ""})
    db.commit()
    return ok({"status": "pending", "msg": "申请已提交"})


@router.get("/phone-grant/pending")
def list_pending_grants(db: Session = Depends(get_db),
                        cur: CurrentUser = Depends(get_current_admin_or_consultant)):
    """待我审批的申请：管理员看全部；老师只看自己名下客户的申请"""
    sql = (
        "SELECT g.id,g.member_id,g.consultant_id,g.reason,g.created_at,"
        "m.name AS member_name,m.enterprise_name,m.consultant_id AS owner_id,"
        "c.name AS applicant_name "
        "FROM customer_phone_grants g "
        "JOIN members m ON m.id=g.member_id "
        "LEFT JOIN consultants c ON c.id=g.consultant_id "
        "WHERE g.status='pending' "
    )
    params = {}
    if not cur.is_admin:
        sql += "AND m.consultant_id=:owner "
        params["owner"] = cur.consultant_id
    sql += "ORDER BY g.created_at DESC"
    rows = db.execute(text(sql), params).mappings().all()
    return ok({"items": [dict(r) for r in rows]})


class GrantReviewIn(BaseModel):
    grant_id: int
    approve: bool


@router.post("/phone-grant/review")
def review_phone_grant(body: GrantReviewIn, db: Session = Depends(get_db),
                       cur: CurrentUser = Depends(get_current_admin_or_consultant)):
    """审批：销售归属老师本人 / 管理员 / 超管"""
    g = db.execute(text(
        "SELECT g.id,g.member_id,m.consultant_id AS owner_id FROM customer_phone_grants g "
        "JOIN members m ON m.id=g.member_id WHERE g.id=:gid AND g.status='pending'"
    ), {"gid": body.grant_id}).mappings().first()
    if not g:
        raise HTTPException(status_code=404, detail="申请不存在或已处理")
    # 权限：管理员，或该客户销售归属本人
    if not (cur.is_admin or (cur.is_consultant and cur.consultant_id == g["owner_id"])):
        raise HTTPException(status_code=403, detail="无权审批该申请")
    if body.approve:
        expire = datetime.utcnow() + timedelta(days=7)
        gtype = "admin" if cur.is_admin else "consultant"
        db.execute(text(
            "UPDATE customer_phone_grants SET status='approved',expire_at=:exp,"
            "granted_by_type=:gt,granted_by_id=:gid2,updated_at=now() WHERE id=:gid"
        ), {"exp": expire, "gt": gtype, "gid2": cur.user_id, "gid": body.grant_id})
    else:
        db.execute(text(
            "UPDATE customer_phone_grants SET status='rejected',updated_at=now() WHERE id=:gid"
        ), {"gid": body.grant_id})
    db.commit()
    return ok({"status": "approved" if body.approve else "rejected"})
