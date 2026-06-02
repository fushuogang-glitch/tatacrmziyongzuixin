"""采购管理 + 储值管理 路由 - 2026-06-02

- /admin/purchases/*   采购管理
- /admin/recharges/*   储值充值管理
- /admin/recharge-consumptions/*  储值消耗记录
- 同时给 agent_api 暴露 /agent/purchases 等只读接口（财务系统拉数）
"""
from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import Purchase, Recharge, RechargeConsumption, Member, Branch
from models.handbook import AdminUser
from utils.auth import get_current_admin

router = APIRouter(tags=["采购+储值管理"])


# ════════════════════════════════════════════════════════════════
#  采购管理
# ════════════════════════════════════════════════════════════════

class PurchaseCreate(BaseModel):
    branch_id: int
    supplier: str
    purchase_date: date
    item: str
    qty: float = 1
    amount: float
    tax_amount: float = 0
    invoice_no: Optional[str] = None
    category: str = "other"
    pay_method: Optional[str] = None
    has_invoice: bool = False
    reimbursed: bool = False
    remark: Optional[str] = None
    receipt_image: Optional[str] = None


class PurchaseUpdate(BaseModel):
    supplier: Optional[str] = None
    purchase_date: Optional[date] = None
    item: Optional[str] = None
    qty: Optional[float] = None
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    invoice_no: Optional[str] = None
    category: Optional[str] = None
    pay_method: Optional[str] = None
    has_invoice: Optional[bool] = None
    reimbursed: Optional[bool] = None
    remark: Optional[str] = None


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    branch_id: int
    branch_name: Optional[str] = None
    supplier: str
    purchase_date: date
    item: str
    qty: float
    amount: float
    tax_amount: float
    invoice_no: Optional[str]
    category: str
    pay_method: Optional[str]
    has_invoice: bool
    reimbursed: bool
    remark: Optional[str]
    receipt_image: Optional[str]
    created_at: datetime
    created_by: Optional[int]


def _enrich_branch(items, db):
    """注入 branch_name"""
    bids = list(set([i.branch_id for i in items if i.branch_id]))
    if not bids:
        return
    bs = {b.id: b.name for b in db.query(Branch).filter(Branch.id.in_(bids)).all()}
    for i in items:
        i.branch_name = bs.get(i.branch_id)


@router.post("/admin/purchases", response_model=PurchaseOut)
def create_purchase(
    data: PurchaseCreate,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """新增采购记录。
    分公司管理员只能录本分公司；超管可录任意分公司。
    """
    # 权限：分公司管理员锁定本分公司
    if getattr(admin, "role", None) == "branch_admin":
        admin_branch = getattr(admin, "branch_id", None)
        if admin_branch and data.branch_id != admin_branch:
            raise HTTPException(403, "仅可为本分公司录入采购")
    
    p = Purchase(**data.model_dump(), created_by=admin.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    _enrich_branch([p], db)
    return p


@router.get("/admin/purchases")
def list_purchases(
    branch_id: Optional[int] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """采购列表。分公司管理员自动按本分公司过滤。"""
    q = db.query(Purchase)
    
    # 分公司管理员只看本分公司
    if getattr(admin, "role", None) == "branch_admin":
        admin_branch = getattr(admin, "branch_id", None)
        if admin_branch:
            q = q.filter(Purchase.branch_id == admin_branch)
    elif branch_id:
        q = q.filter(Purchase.branch_id == branch_id)
    
    if category:
        q = q.filter(Purchase.category == category)
    if start_date:
        q = q.filter(Purchase.purchase_date >= start_date)
    if end_date:
        q = q.filter(Purchase.purchase_date <= end_date)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter((Purchase.supplier.ilike(kw)) | (Purchase.item.ilike(kw)) | (Purchase.invoice_no.ilike(kw)))
    
    total = q.count()
    items = q.order_by(desc(Purchase.purchase_date), desc(Purchase.id)).offset(offset).limit(limit).all()
    _enrich_branch(items, db)
    
    # 汇总
    sum_amount = float(q.with_entities(func.coalesce(func.sum(Purchase.amount), 0)).scalar() or 0)
    sum_tax = float(q.with_entities(func.coalesce(func.sum(Purchase.tax_amount), 0)).scalar() or 0)
    
    return {
        "code": 0,
        "msg": "ok",
        "data": {
            "total": total,
            "sum_amount": sum_amount,
            "sum_tax": sum_tax,
            "items": [PurchaseOut.model_validate(i).model_dump(mode="json") for i in items],
        },
    }


@router.put("/admin/purchases/{pid}", response_model=PurchaseOut)
def update_purchase(
    pid: int,
    data: PurchaseUpdate,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    p = db.query(Purchase).filter(Purchase.id == pid).first()
    if not p:
        raise HTTPException(404, "采购记录不存在")
    if getattr(admin, "role", None) == "branch_admin":
        admin_branch = getattr(admin, "branch_id", None)
        if admin_branch and p.branch_id != admin_branch:
            raise HTTPException(403, "仅可修改本分公司记录")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    _enrich_branch([p], db)
    return p


@router.delete("/admin/purchases/{pid}")
def delete_purchase(
    pid: int,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """删除采购记录（仅超管，按九哥铁律双确认在前端做）"""
    if getattr(admin, "role", None) != "super_admin":
        raise HTTPException(403, "仅超管可删除采购记录")
    p = db.query(Purchase).filter(Purchase.id == pid).first()
    if not p:
        raise HTTPException(404, "采购记录不存在")
    db.delete(p)
    db.commit()
    return {"code": 0, "msg": "已删除"}


# ════════════════════════════════════════════════════════════════
#  储值管理
# ════════════════════════════════════════════════════════════════

class RechargeCreate(BaseModel):
    member_id: int
    title: str
    total_amount: float
    total_count: int = 1
    consultant_id: Optional[int] = None
    branch_id: Optional[int] = None
    payment_id: Optional[int] = None
    package_id: Optional[int] = None
    service_id: Optional[int] = None
    start_date: Optional[date] = None
    expire_date: Optional[date] = None
    remark: Optional[str] = None


class RechargeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    member_id: int
    member_name: Optional[str] = None
    title: str
    total_amount: float
    total_count: int
    used_count: int
    remaining_count: int
    unit_price: Optional[float]
    start_date: Optional[date]
    expire_date: Optional[date]
    status: str
    remark: Optional[str]
    created_at: datetime


class ConsumptionCreate(BaseModel):
    recharge_id: int
    consume_count: int = 1
    consume_date: Optional[date] = None
    consultant_id: Optional[int] = None
    booking_id: Optional[int] = None
    workorder_id: Optional[int] = None
    course_session_id: Optional[int] = None
    remark: Optional[str] = None


@router.post("/admin/recharges", response_model=RechargeOut)
def create_recharge(
    data: RechargeCreate,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """创建一条储值记录（客户买年度套餐时调用）"""
    member = db.query(Member).filter(Member.id == data.member_id).first()
    if not member:
        raise HTTPException(404, "客户不存在")
    
    unit = data.total_amount / data.total_count if data.total_count > 0 else data.total_amount
    
    r = Recharge(
        **data.model_dump(),
        used_count=0,
        remaining_count=data.total_count,
        unit_price=unit,
        status="active",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    r.member_name = member.name
    return r


@router.get("/admin/recharges")
def list_recharges(
    member_id: Optional[int] = None,
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """储值列表"""
    q = db.query(Recharge)
    if member_id:
        q = q.filter(Recharge.member_id == member_id)
    if status:
        q = q.filter(Recharge.status == status)
    if branch_id:
        q = q.filter(Recharge.branch_id == branch_id)
    
    total = q.count()
    items = q.order_by(desc(Recharge.id)).offset(offset).limit(limit).all()
    
    # 注入 member_name
    mids = list(set([r.member_id for r in items]))
    if mids:
        ms = {m.id: m.name for m in db.query(Member).filter(Member.id.in_(mids)).all()}
        for r in items:
            r.member_name = ms.get(r.member_id)
    
    return {
        "code": 0,
        "msg": "ok",
        "data": {
            "total": total,
            "items": [
                {
                    "id": r.id, "member_id": r.member_id, "member_name": getattr(r, "member_name", None),
                    "title": r.title, "total_amount": float(r.total_amount or 0),
                    "total_count": r.total_count, "used_count": r.used_count,
                    "remaining_count": r.remaining_count, "unit_price": float(r.unit_price or 0),
                    "start_date": r.start_date.isoformat() if r.start_date else None,
                    "expire_date": r.expire_date.isoformat() if r.expire_date else None,
                    "status": r.status, "remark": r.remark,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                } for r in items
            ],
        },
    }


@router.get("/admin/members/{member_id}/recharges")
def member_recharges(
    member_id: int,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """客户详情页·储值记录 Tab 用"""
    rs = db.query(Recharge).filter(Recharge.member_id == member_id).order_by(desc(Recharge.id)).all()
    out = []
    for r in rs:
        out.append({
            "id": r.id, "title": r.title,
            "total_amount": float(r.total_amount or 0),
            "total_count": r.total_count, "used_count": r.used_count,
            "remaining_count": r.remaining_count,
            "unit_price": float(r.unit_price or 0),
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "expire_date": r.expire_date.isoformat() if r.expire_date else None,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {"code": 0, "msg": "ok", "data": {"items": out, "total": len(out)}}


@router.post("/admin/recharges/{rid}/consume")
def consume_recharge(
    rid: int,
    data: ConsumptionCreate,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """消耗一次储值（下店执案完成时调用）"""
    r = db.query(Recharge).filter(Recharge.id == rid).first()
    if not r:
        raise HTTPException(404, "储值记录不存在")
    if r.status != "active":
        raise HTTPException(400, f"储值状态 {r.status}，无法消耗")
    if r.remaining_count < data.consume_count:
        raise HTTPException(400, f"剩余次数 {r.remaining_count} 不足 {data.consume_count}")
    
    # 写消耗记录
    c = RechargeConsumption(
        **data.model_dump(),
        member_id=r.member_id,
        branch_id=r.branch_id,
        consume_amount=data.consume_count * float(r.unit_price or 0),
        status="confirmed",
        created_by=admin.id,
    )
    if not c.consume_date:
        c.consume_date = date.today()
    db.add(c)
    
    # 更新储值
    r.used_count += data.consume_count
    r.remaining_count = r.total_count - r.used_count
    if r.remaining_count <= 0:
        r.status = "used_up"
    db.commit()
    
    return {
        "code": 0, "msg": "已扣 1 次",
        "data": {
            "consumption_id": c.id,
            "remaining_count": r.remaining_count,
            "status": r.status,
        },
    }


@router.get("/admin/recharges/{rid}/consumptions")
def list_consumptions(
    rid: int,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    cs = db.query(RechargeConsumption).filter(RechargeConsumption.recharge_id == rid).order_by(desc(RechargeConsumption.id)).all()
    return {
        "code": 0, "msg": "ok",
        "data": {
            "items": [
                {
                    "id": c.id, "consume_date": c.consume_date.isoformat(),
                    "consume_count": c.consume_count, "consume_amount": float(c.consume_amount or 0),
                    "consultant_id": c.consultant_id, "booking_id": c.booking_id,
                    "status": c.status, "remark": c.remark,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                } for c in cs
            ],
            "total": len(cs),
        },
    }
