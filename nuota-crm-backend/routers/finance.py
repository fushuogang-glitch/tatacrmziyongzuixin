"""财务管理 v2.2 — 分公司盈亏平衡核算 + 月度独立记账
组织维度：branch（分公司）
数据源：payments(收入) + purchases(采购变动成本) + salary_records(工资) + branch_fixed_costs(固定成本)
权限：超管全部 / 分公司 admin 仅本店
"""
from datetime import date, datetime
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, text, and_
from sqlalchemy.orm import Session

from database import get_db
from models import Branch
from models.purchase import Purchase
from models.finance import BranchFixedCost, BranchBreakevenConfig
from utils.auth import get_current_admin
from utils.helpers import ok

router = APIRouter(prefix="/admin/finance", tags=["财务管理"])


def D(x) -> float:
    return float(x or 0)


def _month_range(month: str):
    y, m = int(month[:4]), int(month[5:7])
    start = date(y, m, 1)
    end = date(y + (m // 12), (m % 12) + 1, 1)
    return start, end


def _branch_scope(admin):
    """返回(是否超管, 限定branch_id或None)"""
    role = getattr(admin, "role", None)
    if role == "super_admin":
        return True, None
    return False, getattr(admin, "branch_id", None)


def _check_branch(admin, bid: int):
    is_super, my_branch = _branch_scope(admin)
    if not is_super and my_branch and my_branch != bid:
        raise HTTPException(403, "仅可查看本分公司财务")


# ───────── 单分公司月度核算 ─────────
def _branch_monthly(db: Session, bid: int, month: str) -> dict:
    start, end = _month_range(month)

    # 收入：payments 当月（已支付）
    income = db.execute(text(
        "SELECT COALESCE(SUM(amount),0) FROM payments "
        "WHERE branch_id=:bid AND pay_time>=:s AND pay_time<:e "
        "AND (pay_status IS NULL OR pay_status IN ('paid','success','已支付',''))"
    ), {"bid": bid, "s": start, "e": end}).scalar()
    income = D(income)

    # 采购（变动成本）
    purchase = db.execute(text(
        "SELECT COALESCE(SUM(amount),0) FROM purchases "
        "WHERE branch_id=:bid AND purchase_date>=:s AND purchase_date<:e"
    ), {"bid": bid, "s": start, "e": end}).scalar()
    purchase = D(purchase)

    # 差旅类采购（category=travel 计入变动）已含在 purchase 里
    # 工资：salary_records 当月（底薪=固定，提成=变动）
    y, m = int(month[:4]), int(month[5:7])
    sal = db.execute(text(
        "SELECT COALESCE(SUM(base_salary),0) AS base, COALESCE(SUM(commission_amount),0) AS comm, "
        "COALESCE(SUM(total_salary),0) AS total FROM salary_records sr "
        "JOIN consultants c ON c.id=sr.consultant_id "
        "WHERE c.branch_id=:bid AND sr.year=:y AND sr.month=:m"
    ), {"bid": bid, "y": y, "m": m}).mappings().first()
    base_salary = D(sal["base"]) if sal else 0
    commission = D(sal["comm"]) if sal else 0
    salary_total = D(sal["total"]) if sal else 0

    # 固定成本：branch_fixed_costs 当月
    fixed_other = db.execute(text(
        "SELECT COALESCE(SUM(amount),0) FROM branch_fixed_costs "
        "WHERE branch_id=:bid AND cost_month=:mon"
    ), {"bid": bid, "mon": month}).scalar()
    fixed_other = D(fixed_other)

    # 固定成本明细（按科目）
    fixed_detail = db.execute(text(
        "SELECT category, COALESCE(SUM(amount),0) amt FROM branch_fixed_costs "
        "WHERE branch_id=:bid AND cost_month=:mon GROUP BY category"
    ), {"bid": bid, "mon": month}).mappings().all()

    # 消耗额：老师下店执案消耗（recharge_consumptions + package_consumptions）按分公司+月汇总
    rc = db.execute(text(
        "SELECT COALESCE(SUM(consume_amount),0) FROM recharge_consumptions "
        "WHERE branch_id=:bid AND consume_date>=:s AND consume_date<:e"
    ), {"bid": bid, "s": start, "e": end}).scalar()
    # package_consumptions 无 branch_id，按 consultant 所属分公司归集
    pc = db.execute(text(
        "SELECT COALESCE(SUM(pc.deducted_amount),0) FROM package_consumptions pc "
        "JOIN consultants c ON c.id=pc.consultant_id "
        "WHERE c.branch_id=:bid AND pc.appoint_date>=:s AND pc.appoint_date<:e"
    ), {"bid": bid, "s": start, "e": end}).scalar()
    consumption = D(rc) + D(pc)

    # 盈亏平衡参数
    cfg = db.query(BranchBreakevenConfig).filter(BranchBreakevenConfig.branch_id == bid).first()
    default_var_rate = D(cfg.default_variable_rate) if cfg else 0.35

    # 固定成本合计 = 其他固定 + 工资底薪
    fixed_cost = fixed_other + base_salary
    # 变动成本合计 = 采购 + 提成
    variable_cost = purchase + commission

    total_cost = fixed_cost + variable_cost
    profit = income - total_cost

    # 双口径利润率
    profit_rate_income = (profit / income) if income > 0 else None              # 按营业额
    profit_consumption = consumption - total_cost
    profit_rate_consumption = (profit_consumption / consumption) if consumption > 0 else None  # 按消耗额

    # 变动成本率
    if income > 0:
        var_rate = variable_cost / income
    else:
        var_rate = default_var_rate
    # 防御：变动成本率 >=1 会导致平衡点无意义
    if var_rate >= 1:
        var_rate = min(var_rate, 0.95)
    breakeven = fixed_cost / (1 - var_rate) if (1 - var_rate) > 0 else None
    achieve_rate = (income / breakeven) if breakeven else None

    return {
        "branch_id": bid,
        "month": month,
        "income": round(income, 2),
        "fixed_cost": round(fixed_cost, 2),
        "fixed_breakdown": {
            "base_salary": round(base_salary, 2),
            "rent_utility_other": round(fixed_other, 2),
            "by_category": {d["category"]: round(D(d["amt"]), 2) for d in fixed_detail},
        },
        "variable_cost": round(variable_cost, 2),
        "variable_breakdown": {"purchase": round(purchase, 2), "commission": round(commission, 2)},
        "total_cost": round(total_cost, 2),
        "salary_total": round(salary_total, 2),
        "profit": round(profit, 2),
        "is_profit": profit >= 0,
        "variable_rate": round(var_rate, 4),
        "breakeven_point": round(breakeven, 2) if breakeven else None,
        "achieve_rate": round(achieve_rate, 4) if achieve_rate else None,
        "gap_to_breakeven": round(breakeven - income, 2) if breakeven else None,
        "consumption": round(consumption, 2),
        "profit_by_consumption": round(profit_consumption, 2),
        "profit_rate_income": round(profit_rate_income, 4) if profit_rate_income is not None else None,
        "profit_rate_consumption": round(profit_rate_consumption, 4) if profit_rate_consumption is not None else None,
    }


@router.get("/branch/{bid}/monthly")
def branch_monthly(bid: int, month: str = Query(..., description="YYYY-MM"),
                   db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    _check_branch(admin, bid)
    b = db.query(Branch).filter(Branch.id == bid).first()
    if not b:
        raise HTTPException(404, "分公司不存在")
    data = _branch_monthly(db, bid, month)
    data["branch_name"] = b.name
    data["city"] = b.city
    return ok(data)


@router.get("/branch/{bid}/breakeven")
def branch_breakeven(bid: int, month: str = Query(...),
                     db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """盈亏平衡点详算（含公式拆解）"""
    _check_branch(admin, bid)
    d = _branch_monthly(db, bid, month)
    d["formula"] = "盈亏平衡点 = 固定成本 ÷ (1 - 变动成本率)"
    d["explain"] = (
        f"固定成本 ¥{d['fixed_cost']}（底薪{d['fixed_breakdown']['base_salary']}+房租水电等{d['fixed_breakdown']['rent_utility_other']}）"
        f" ÷ (1 - 变动成本率 {round(d['variable_rate']*100,1)}%) = 平衡点 ¥{d['breakeven_point']}"
    )
    return ok(d)


# ───────── 全公司总览 ─────────
@router.get("/overview")
def overview(month: str = Query(..., description="YYYY-MM"),
             db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    is_super, my_branch = _branch_scope(admin)
    q = db.query(Branch).filter(Branch.status != "disabled")
    if not is_super and my_branch:
        q = q.filter(Branch.id == my_branch)
    branches = q.all()

    items = []
    tot_income = tot_fixed = tot_var = tot_profit = tot_consume = 0.0
    for b in branches:
        m = _branch_monthly(db, b.id, month)
        m["branch_name"] = b.name
        m["city"] = b.city
        items.append(m)
        tot_income += m["income"]; tot_fixed += m["fixed_cost"]
        tot_var += m["variable_cost"]; tot_profit += m["profit"]
        tot_consume += m["consumption"]
    items.sort(key=lambda x: -x["profit"])
    tot_cost = tot_fixed + tot_var
    return ok({
        "month": month,
        "summary": {
            "total_income": round(tot_income, 2),
            "total_consumption": round(tot_consume, 2),
            "total_fixed_cost": round(tot_fixed, 2),
            "total_variable_cost": round(tot_var, 2),
            "total_cost": round(tot_cost, 2),
            "total_profit": round(tot_profit, 2),
            "profit_rate_income": round(tot_profit / tot_income, 4) if tot_income > 0 else None,
            "profit_rate_consumption": round((tot_consume - tot_cost) / tot_consume, 4) if tot_consume > 0 else None,
            "branch_count": len(items),
            "profitable_count": sum(1 for x in items if x["is_profit"]),
        },
        "branches": items,
    })


# ───────── 收支明细 ─────────
@router.get("/income-detail")
def income_detail(month: str = Query(...), branch_id: Optional[int] = None,
                  db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    is_super, my_branch = _branch_scope(admin)
    if not is_super:
        branch_id = my_branch
    start, end = _month_range(month)
    sql = ("SELECT p.id,p.amount,p.pay_method,p.pay_time,p.remark,p.branch_id,"
           "m.name member_name,b.name branch_name "
           "FROM payments p LEFT JOIN members m ON m.id=p.member_id "
           "LEFT JOIN branches b ON b.id=p.branch_id "
           "WHERE p.pay_time>=:s AND p.pay_time<:e ")
    params = {"s": start, "e": end}
    if branch_id:
        sql += "AND p.branch_id=:bid "; params["bid"] = branch_id
    sql += "ORDER BY p.pay_time DESC"
    rows = db.execute(text(sql), params).mappings().all()
    total = sum(D(r["amount"]) for r in rows)
    return ok({"total": round(total, 2), "count": len(rows), "items": [dict(r) for r in rows]})


@router.get("/expense-detail")
def expense_detail(month: str = Query(...), branch_id: Optional[int] = None,
                   db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    is_super, my_branch = _branch_scope(admin)
    if not is_super:
        branch_id = my_branch
    start, end = _month_range(month)
    # 采购
    psql = ("SELECT 'purchase' kind, p.id, p.amount, p.item desc_, p.category, p.purchase_date dt, "
            "b.name branch_name, p.branch_id FROM purchases p LEFT JOIN branches b ON b.id=p.branch_id "
            "WHERE p.purchase_date>=:s AND p.purchase_date<:e ")
    params = {"s": start, "e": end}
    if branch_id:
        psql += "AND p.branch_id=:bid "; params["bid"] = branch_id
    purchases = db.execute(text(psql), params).mappings().all()
    # 固定成本
    fsql = ("SELECT 'fixed' kind, f.id, f.amount, f.item desc_, f.category, f.cost_month dt, "
            "b.name branch_name, f.branch_id FROM branch_fixed_costs f LEFT JOIN branches b ON b.id=f.branch_id "
            "WHERE f.cost_month=:mon ")
    fparams = {"mon": month}
    if branch_id:
        fsql += "AND f.branch_id=:bid "; fparams["bid"] = branch_id
    fixed = db.execute(text(fsql), fparams).mappings().all()
    items = [dict(r) for r in purchases] + [dict(r) for r in fixed]
    total = sum(D(r["amount"]) for r in items)
    return ok({"total": round(total, 2), "count": len(items), "items": items})


# ───────── 固定成本 CRUD ─────────
class FixedCostIn(BaseModel):
    branch_id: int
    cost_month: str
    category: str = "other_fixed"
    item: str
    amount: float
    remark: Optional[str] = None


@router.get("/fixed-costs")
def list_fixed_costs(month: Optional[str] = None, branch_id: Optional[int] = None,
                     db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    is_super, my_branch = _branch_scope(admin)
    q = db.query(BranchFixedCost)
    if not is_super and my_branch:
        q = q.filter(BranchFixedCost.branch_id == my_branch)
    elif branch_id:
        q = q.filter(BranchFixedCost.branch_id == branch_id)
    if month:
        q = q.filter(BranchFixedCost.cost_month == month)
    rows = q.order_by(BranchFixedCost.cost_month.desc()).all()
    out = []
    for r in rows:
        out.append({c.name: getattr(r, c.name) for c in r.__table__.columns})
    return ok({"items": out})


@router.post("/fixed-costs")
def create_fixed_cost(body: FixedCostIn, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    _check_branch(admin, body.branch_id)
    rec = BranchFixedCost(
        branch_id=body.branch_id, cost_month=body.cost_month, category=body.category,
        item=body.item, amount=body.amount, remark=body.remark, created_by=getattr(admin, "id", None),
    )
    db.add(rec)
    db.commit(); db.refresh(rec)
    return ok({"id": rec.id})


@router.put("/fixed-costs/{fid}")
def update_fixed_cost(fid: int, body: FixedCostIn, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    rec = db.query(BranchFixedCost).filter(BranchFixedCost.id == fid).first()
    if not rec:
        raise HTTPException(404, "记录不存在")
    _check_branch(admin, rec.branch_id)
    for k in ("cost_month", "category", "item", "amount", "remark"):
        setattr(rec, k, getattr(body, k))
    db.commit()
    return ok({"id": rec.id})


@router.delete("/fixed-costs/{fid}")
def delete_fixed_cost(fid: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    rec = db.query(BranchFixedCost).filter(BranchFixedCost.id == fid).first()
    if not rec:
        raise HTTPException(404, "记录不存在")
    _check_branch(admin, rec.branch_id)
    db.delete(rec); db.commit()
    return ok({"deleted": fid})


# ───────── 盈亏平衡参数 ─────────
class BreakevenCfgIn(BaseModel):
    commission_rate: Optional[float] = None
    variable_extra_rate: Optional[float] = None
    default_variable_rate: Optional[float] = None


@router.get("/branch/{bid}/breakeven-config")
def get_be_config(bid: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    _check_branch(admin, bid)
    cfg = db.query(BranchBreakevenConfig).filter(BranchBreakevenConfig.branch_id == bid).first()
    if not cfg:
        return ok({"branch_id": bid, "commission_rate": 0.05, "variable_extra_rate": 0, "default_variable_rate": 0.35})
    return ok({c.name: getattr(cfg, c.name) for c in cfg.__table__.columns})


@router.put("/branch/{bid}/breakeven-config")
def set_be_config(bid: int, body: BreakevenCfgIn, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    _check_branch(admin, bid)
    cfg = db.query(BranchBreakevenConfig).filter(BranchBreakevenConfig.branch_id == bid).first()
    if not cfg:
        cfg = BranchBreakevenConfig(branch_id=bid)
        db.add(cfg)
    if body.commission_rate is not None:
        cfg.commission_rate = body.commission_rate
    if body.variable_extra_rate is not None:
        cfg.variable_extra_rate = body.variable_extra_rate
    if body.default_variable_rate is not None:
        cfg.default_variable_rate = body.default_variable_rate
    db.commit()
    return ok({"branch_id": bid})
