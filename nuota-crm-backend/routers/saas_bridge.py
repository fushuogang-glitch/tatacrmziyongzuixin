"""
SaaS Bridge - 塔塔财务系统标准接入接口
============================================
专为财务系统 saas-integration.ts 设计的 5 个标准接口：
  /api/agent/ping
  /api/agent/members/topups       充值（pay_type=package）
  /api/agent/members/consumes     消费（pay_type=single）
  /api/agent/store/daily-revenue  日营收
  /api/agent/payroll              工资（塔塔CRM暂无员工模块·返回空）
  /api/agent/purchases            进货（塔塔CRM暂无进货模块·返回空）

鉴权：复用 X-Api-Key 机制
租户：塔塔CRM 是单店·storeCode 任意都返回本店数据
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from database import get_db
from models import Payment, Member
from routers.agent_api import _require_agent, AgentAuth, _ok

router = APIRouter(prefix="/api/agent", tags=["SaaS Bridge·财务对接"])

STORE_CODE = "TATA-SH-001"  # 塔塔咨询单店编码
STORE_NAME = "塔塔咨询·总部"


def _parse_date(s: Optional[str], default: Optional[date] = None) -> Optional[date]:
    if not s:
        return default
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return default


@router.get("/ping")
def saas_ping(agent: AgentAuth = Depends(_require_agent)):
    """财务系统连接测试"""
    return {
        "ok": True,
        "storeCount": 1,
        "storeName": STORE_NAME,
        "storeCode": STORE_CODE,
        "agent": agent.agent_name,
        "ts": datetime.now().isoformat(),
    }


@router.get("/members/topups")
def saas_topups(
    storeCode: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """充值流水·pay_type=package（套餐充值=预收账款）"""
    df = _parse_date(from_, date.today() - timedelta(days=90))
    dt = _parse_date(to, date.today())
    q = (
        db.query(Payment)
        .filter(Payment.pay_type.in_(["package", "annual"]))
        .filter(Payment.pay_status == "paid")
        .filter(Payment.created_at >= df)
        .filter(Payment.created_at <= datetime.combine(dt, datetime.max.time()))
        .order_by(desc(Payment.created_at))
    )
    rows = q.all()
    items = []
    for p in rows:
        m = db.query(Member).filter(Member.id == p.member_id).first() if p.member_id else None
        items.append({
            "id": p.id,
            "memberNo": f"M{p.member_id:06d}" if p.member_id else "",
            "memberName": (m.name if m else "") or "",
            "amount": float(p.amount or 0),
            "bonus": 0.0,
            "channel": p.pay_method or "",
            "storeCode": STORE_CODE,
            "occurredAt": (p.pay_time or p.created_at).isoformat() if (p.pay_time or p.created_at) else "",
            "remark": p.remark or "",
        })
    return items  # 财务端按数组解析


@router.get("/members/consumes")
def saas_consumes(
    storeCode: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """消费流水·pay_type=single（单次/营业收入）"""
    df = _parse_date(from_, date.today() - timedelta(days=90))
    dt = _parse_date(to, date.today())
    q = (
        db.query(Payment)
        .filter(Payment.pay_type == "single")
        .filter(Payment.pay_status == "paid")
        .filter(Payment.created_at >= df)
        .filter(Payment.created_at <= datetime.combine(dt, datetime.max.time()))
        .order_by(desc(Payment.created_at))
    )
    rows = q.all()
    items = []
    for p in rows:
        m = db.query(Member).filter(Member.id == p.member_id).first() if p.member_id else None
        items.append({
            "id": p.id,
            "memberNo": f"M{p.member_id:06d}" if p.member_id else "",
            "memberName": (m.name if m else "") or "",
            "amount": float(p.amount or 0),
            "channel": p.pay_method or "",
            "storeCode": STORE_CODE,
            "serviceCode": str(p.service_id or ""),
            "serviceName": "",  # 后续 enrich
            "occurredAt": (p.pay_time or p.created_at).isoformat() if (p.pay_time or p.created_at) else "",
            "remark": p.remark or "",
        })
    return items


@router.get("/store/daily-revenue")
def saas_daily_revenue(
    storeCode: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """日营收·按日聚合 paid 状态的 payments"""
    df = _parse_date(from_, date.today() - timedelta(days=30))
    dt = _parse_date(to, date.today())
    rows = (
        db.query(
            func.date(Payment.created_at).label("d"),
            func.sum(Payment.amount).label("amt"),
            func.count(Payment.id).label("cnt"),
        )
        .filter(Payment.pay_status == "paid")
        .filter(Payment.created_at >= df)
        .filter(Payment.created_at <= datetime.combine(dt, datetime.max.time()))
        .group_by(func.date(Payment.created_at))
        .order_by(func.date(Payment.created_at))
        .all()
    )
    return [
        {
            "date": r.d.isoformat() if r.d else "",
            "storeCode": STORE_CODE,
            "amount": float(r.amt or 0),
            "orderCount": int(r.cnt or 0),
        }
        for r in rows
    ]


@router.get("/payroll")
def saas_payroll(
    storeCode: Optional[str] = None,
    period: Optional[str] = None,
    agent: AgentAuth = Depends(_require_agent),
):
    """工资·塔塔CRM 暂无员工工资模块·返回空数组"""
    return []


@router.get("/purchases")
def saas_purchases(
    storeCode: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    agent: AgentAuth = Depends(_require_agent),
):
    """进货·塔塔CRM 暂无进货模块·返回空数组"""
    return []
