"""
Agent 统一业务 API — /agent/* 前缀
所有Agent通过 X-Api-Key 认证，复用现有ORM模型。
readonly Agent 不能 POST/PUT/PATCH。

模块清单:
 - 三和 (sanhe/client-officer) → 客户管理（读写）
 - 七星 (qixing/content-officer) → 内容管理（读写）
 - 五路 (wulu/hr-assistant) → 组织管理（读写）
 - 百川 (baichuan/finance-officer) → 财务（只读）
 - 二福 (erfu/data-officer) → 数据（只读）
 - 九亿 (jiuyi/main) → 服务项目管理（读写）
 - 司库 (siku/sikuagent) → 备份巡检（只读）
"""
import csv
import io
import json
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, text, desc, cast, String
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models.member import Member, Payment
from models.service import Service, ServicePackage, ServiceOrder, ServiceWorkLog
from models.booking import Consultant, ConsultantSchedule
from models.followup import FollowUp
from models.agent import AgentApiKey
from models.webhook_event import WebhookEvent
from utils.agent_auth import AgentAuth, get_agent_auth

logger = logging.getLogger("agent_api")

router = APIRouter(prefix="/agent", tags=["Agent业务API"])


# ══════════════════════════════════════════════════════════════
#  认证 & 权限
# ══════════════════════════════════════════════════════════════

def _require_agent(agent: Optional[AgentAuth] = Depends(get_agent_auth)) -> AgentAuth:
    """强制要求 Agent 认证，非 Agent 请求直接 401"""
    if agent is None:
        raise HTTPException(status_code=401, detail="缺少 X-Api-Key 认证头")
    return agent


def _require_write(agent: AgentAuth = Depends(_require_agent)) -> AgentAuth:
    """写操作：readonly Agent 直接 403"""
    if agent.is_readonly:
        raise HTTPException(status_code=403, detail=f"Agent [{agent.agent_name}] 只有只读权限，不能执行写操作")
    return agent


def _ok(data: Any = None, msg: str = "ok") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def _serialize(obj, fields=None) -> dict:
    """ORM 对象序列化"""
    if obj is None:
        return {}
    if fields is None:
        fields = [c.name for c in obj.__table__.columns]
    out = {}
    for f in fields:
        v = getattr(obj, f, None)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        elif isinstance(v, Decimal):
            v = float(v)
        out[f] = v
    return out




def _enrich(items: list, db, enrich_map: dict = None) -> list:
    """批量补充关联名字。enrich_map = {"consultant_id": "consultant_name", ...}"""
    if not items or not enrich_map:
        return items
    from models.booking import Consultant
    from models.member import Member
    from models.service import Service
    # 收集需要查的ID
    consultant_ids = set()
    member_ids = set()
    service_ids = set()
    for item in items:
        for fk in enrich_map:
            v = item.get(fk)
            if v and isinstance(v, int):
                if "consultant" in fk or "assistant" in fk:
                    consultant_ids.add(v)
                elif "member" in fk:
                    member_ids.add(v)
                elif "service" in fk:
                    service_ids.add(v)
    # 批量查
    c_map = {}
    if consultant_ids:
        rows = db.query(Consultant.id, Consultant.name).filter(Consultant.id.in_(consultant_ids)).all()
        c_map = {r.id: r.name for r in rows}
    m_map = {}
    if member_ids:
        rows = db.query(Member.id, Member.name).filter(Member.id.in_(member_ids)).all()
        m_map = {r.id: r.name for r in rows}
    s_map = {}
    if service_ids:
        rows = db.query(Service.id, Service.name).filter(Service.id.in_(service_ids)).all()
        s_map = {r.id: r.name for r in rows}
    # 注入
    for item in items:
        for fk, target_field in enrich_map.items():
            v = item.get(fk)
            if v and isinstance(v, int):
                if "consultant" in fk or "assistant" in fk:
                    item[target_field] = c_map.get(v)
                elif "member" in fk:
                    item[target_field] = m_map.get(v)
                elif "service" in fk:
                    item[target_field] = s_map.get(v)
    return items

# ══════════════════════════════════════════════════════════════
#  1. 三和 — 客户管理（读写）
# ══════════════════════════════════════════════════════════════

# ── 工单 ──

class WorkOrderCreate(BaseModel):
    member_id: Optional[int] = None
    service_id: Optional[int] = None
    consultant_id: Optional[int] = None
    assistant_id: Optional[int] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    appoint_date: Optional[str] = None        # YYYY-MM-DD
    appoint_time: Optional[str] = None
    remark: Optional[str] = None


class WorkOrderStatusUpdate(BaseModel):
    status: str   # pending/confirmed/in_progress/completed/cancelled


@router.get("/workorders")
def list_workorders(
    status: Optional[str] = None,
    member_id: Optional[int] = None,
    consultant_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """工单列表（支持 status / member_id / consultant_id 筛选）"""
    q = db.query(ServiceOrder)
    if status:
        q = q.filter(ServiceOrder.status == status)
    if member_id:
        q = q.filter(ServiceOrder.member_id == member_id)
    if consultant_id:
        q = q.filter(ServiceOrder.consultant_id == consultant_id)
    total = q.count()
    items = q.order_by(desc(ServiceOrder.id)).offset(offset).limit(limit).all()
    items_data = [_serialize(o) for o in items]
    _enrich(items_data, db, {"consultant_id": "consultant_name", "assistant_id": "assistant_name", "member_id": "member_name", "service_id": "service_name"})
    return _ok({"total": total, "items": items_data})




@router.get("/workorders/{order_id}")
def get_workorder(
    order_id: int,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """单条工单详情"""
    order = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "工单不存在")
    data = _serialize(order)
    _enrich([data], db, {"consultant_id": "consultant_name", "assistant_id": "assistant_name", "member_id": "member_name", "service_id": "service_name"})
    return _ok(data)

@router.post("/workorders")
def create_workorder(
    body: WorkOrderCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """创建工单"""
    # 生成工单号
    today_str = date.today().strftime("%Y%m%d")
    count = db.query(func.count(ServiceOrder.id)).filter(
        ServiceOrder.order_no.like(f"SO-{today_str}%")
    ).scalar() or 0
    order_no = f"SO-{today_str}-{count + 1:03d}"

    order = ServiceOrder(
        order_no=order_no,
        member_id=body.member_id,
        service_id=body.service_id,
        consultant_id=body.consultant_id,
        assistant_id=body.assistant_id,
        store_name=body.store_name,
        store_address=body.store_address,
        appoint_date=datetime.strptime(body.appoint_date, "%Y-%m-%d").date() if body.appoint_date else None,
        appoint_time=body.appoint_time,
        status="pending",
        remark=body.remark,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # 发射事件
    _emit_event(db, "booking.created", {"order_id": order.id, "order_no": order_no})
    return _ok(_serialize(order), "工单创建成功")


@router.patch("/workorders/{order_id}/status")
def update_workorder_status(
    order_id: int,
    body: WorkOrderStatusUpdate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """更新工单状态"""
    order = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "工单不存在")
    old_status = order.status
    order.status = body.status
    db.commit()

    # 工单确认→发事件
    if body.status == "confirmed" and old_status != "confirmed":
        _emit_event(db, "order.confirmed", {"order_id": order.id, "order_no": order.order_no})
    # 工单完结→发事件
    if body.status == "completed" and old_status != "completed":
        _emit_event(db, "order.completed", {"order_id": order.id, "order_no": order.order_no, "member_id": order.member_id})

    return _ok({"id": order.id, "status": order.status, "old_status": old_status})


# ── 会员 ──

class MemberCreate(BaseModel):
    name: str
    phone: str
    enterprise_name: Optional[str] = None
    store_count: Optional[int] = 1
    store_type: Optional[str] = None
    city: Optional[str] = None
    role: Optional[str] = None
    member_type: Optional[str] = "trial"
    gender: Optional[str] = "female"
    consultant_id: Optional[int] = None
    tags: Optional[str] = None
    notes: Optional[str] = None


@router.get("/members")
def list_members(
    status: Optional[str] = None,
    member_type: Optional[str] = None,
    consultant_id: Optional[int] = None,
    keyword: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """会员列表"""
    q = db.query(Member)
    if status:
        q = q.filter(Member.status == status)
    if member_type:
        q = q.filter(Member.member_type == member_type)
    if consultant_id:
        q = q.filter(Member.consultant_id == consultant_id)
    if keyword:
        q = q.filter(
            (Member.name.ilike(f"%{keyword}%")) | (Member.phone.ilike(f"%{keyword}%"))
        )
    total = q.count()
    items = q.order_by(desc(Member.id)).offset(offset).limit(limit).all()
    items_data = [_serialize(o) for o in items]
    _enrich(items_data, db, {"consultant_id": "consultant_name"})
    return _ok({"total": total, "items": items_data})




@router.get("/members/{member_id}")
def get_member(
    member_id: int,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """单条客户详情"""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(404, "客户不存在")
    data = _serialize(member)
    _enrich([data], db, {"consultant_id": "consultant_name"})
    return _ok(data)

@router.post("/members")
def create_member(
    body: MemberCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """新建会员"""
    # 检查手机号重复
    exist = db.query(Member).filter(Member.phone == body.phone).first()
    if exist:
        raise HTTPException(400, f"手机号 {body.phone} 已存在（会员ID: {exist.id}）")

    # 生成编号
    from utils.helpers import gen_member_no, gen_referral_code
    member = Member(
        name=body.name,
        phone=body.phone,
        enterprise_name=body.enterprise_name,
        store_count=body.store_count,
        store_type=body.store_type,
        city=body.city,
        role=body.role,
        member_type=body.member_type,
        member_no=gen_member_no(db),
        referral_code=gen_referral_code(),
        gender=body.gender,
        consultant_id=body.consultant_id,
        tags=body.tags,
        notes=body.notes,
        status="active",
        enroll_date=date.today(),
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    _emit_event(db, "member.created", {"member_id": member.id, "name": member.name})
    return _ok(_serialize(member), "会员创建成功")


# ── 跟进记录 ──

class FollowupCreate(BaseModel):
    content: str
    follow_type: Optional[str] = "note"       # note/call/visit/wechat
    status: Optional[str] = "following"
    next_follow_date: Optional[str] = None     # ISO datetime
    admin_name: Optional[str] = None




class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    enterprise_name: Optional[str] = None
    store_count: Optional[int] = None
    store_type: Optional[str] = None
    city: Optional[str] = None
    role: Optional[str] = None
    member_type: Optional[str] = None
    gender: Optional[str] = None
    consultant_id: Optional[int] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


@router.patch("/members/{member_id}")
def update_member(
    member_id: int,
    body: MemberUpdate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """更新客户信息"""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(404, "客户不存在")
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "没有需要更新的字段")
    for k, v in updates.items():
        setattr(member, k, v)
    db.commit()
    db.refresh(member)
    _emit_event(db, "member.updated", {"member_id": member.id, "fields": list(updates.keys())})
    data = _serialize(member)
    _enrich([data], db, {"consultant_id": "consultant_name"})
    return _ok(data, "客户信息已更新")

@router.get("/members/{member_id}/followup")
def list_followups(
    member_id: int,
    limit: int = Query(50, le=200),
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """查询跟进记录"""
    items = (
        db.query(FollowUp)
        .filter(FollowUp.member_id == member_id)
        .order_by(desc(FollowUp.id))
        .limit(limit)
        .all()
    )
    return _ok([_serialize(f) for f in items])


@router.post("/members/{member_id}/followup")
def create_followup(
    member_id: int,
    body: FollowupCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """新增跟进记录"""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(404, "会员不存在")

    fu = FollowUp(
        member_id=member_id,
        content=body.content,
        follow_type=body.follow_type,
        status=body.status,
        admin_name=body.admin_name or agent.agent_name,
        next_follow_date=datetime.fromisoformat(body.next_follow_date) if body.next_follow_date else None,
    )
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return _ok(_serialize(fu), "跟进记录已创建")


# ── 收款记录 ──

class PaymentCreate(BaseModel):
    member_id: int
    amount: float
    pay_method: Optional[str] = "company_account"
    pay_type: Optional[str] = "annual"
    service_id: Optional[int] = None
    package_id: Optional[int] = None
    consultant_id: Optional[int] = None
    remark: Optional[str] = None


@router.post("/payments")
def create_payment(
    body: PaymentCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """录入收款记录"""
    member = db.query(Member).filter(Member.id == body.member_id).first()
    if not member:
        raise HTTPException(404, "会员不存在")

    p = Payment(
        member_id=body.member_id,
        amount=body.amount,
        pay_method=body.pay_method,
        pay_type=body.pay_type,
        pay_status="paid",
        service_id=body.service_id,
        package_id=body.package_id,
        consultant_id=body.consultant_id or member.consultant_id,
        pay_time=datetime.utcnow(),
        remark=body.remark,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    _emit_event(db, "payment.created", {"payment_id": p.id, "member_id": body.member_id, "amount": float(body.amount)})
    return _ok(_serialize(p), "收款记录已创建")


# ── 排期 ──

class ScheduleCreate(BaseModel):
    consultant_id: int
    schedule_date: str             # YYYY-MM-DD
    city: Optional[str] = None
    schedule_type: Optional[str] = "available"
    title: Optional[str] = None
    remark: Optional[str] = None
    order_id: Optional[int] = None


@router.get("/schedule")
def list_schedule(
    consultant_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, le=500),
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """排期查询"""
    q = db.query(ConsultantSchedule)
    if consultant_id:
        q = q.filter(ConsultantSchedule.consultant_id == consultant_id)
    if start_date:
        q = q.filter(ConsultantSchedule.schedule_date >= start_date)
    if end_date:
        q = q.filter(ConsultantSchedule.schedule_date <= end_date)
    items = q.order_by(ConsultantSchedule.schedule_date).limit(limit).all()
    items_data = [_serialize(s) for s in items]
    _enrich(items_data, db, {"consultant_id": "consultant_name"})
    return _ok(items_data)


@router.post("/schedule")
def create_schedule(
    body: ScheduleCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """创建排期"""
    s = ConsultantSchedule(
        consultant_id=body.consultant_id,
        schedule_date=datetime.strptime(body.schedule_date, "%Y-%m-%d").date(),
        city=body.city,
        schedule_type=body.schedule_type,
        title=body.title,
        remark=body.remark,
        order_id=body.order_id,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _ok(_serialize(s), "排期已创建")


# ── 通知 ──

class NotifyRequest(BaseModel):
    member_id: Optional[int] = None
    consultant_id: Optional[int] = None
    target: Optional[str] = None            # wecom_userid / phone
    title: str
    content: str
    channel: Optional[str] = "wecom"        # wecom/sms/system


@router.post("/notify")
def send_notify(
    body: NotifyRequest,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """推送企微通知（记录，后续接入实际推送通道）"""
    # TODO: 接入企微机器人 / 消息推送通道
    logger.info(f"[NOTIFY] agent={agent.agent_id} channel={body.channel} title={body.title}")
    return _ok({
        "channel": body.channel,
        "title": body.title,
        "status": "recorded",
        "msg": "通知已记录，待接入推送通道",
    })


# ══════════════════════════════════════════════════════════════
#  2. 七星 — 内容管理（读写）
# ══════════════════════════════════════════════════════════════

class ContentCreate(BaseModel):
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    cover_image: Optional[str] = None
    video_url: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[str] = None
    brand: Optional[str] = "塔塔"
    status: Optional[str] = "draft"          # draft/published


@router.post("/content/brand-news")
def publish_brand_news(
    body: ContentCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """发布品牌动态"""
    return _create_article(db, body, category="brand_news", agent=agent)


@router.post("/content/industry-news")
def publish_industry_news(
    body: ContentCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """发布行业动态"""
    return _create_article(db, body, category="industry", agent=agent)


@router.post("/content/culture")
def publish_culture(
    body: ContentCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """增加企业文化内容"""
    return _create_article(db, body, category="culture", agent=agent)


def _create_article(db: DBSession, body: ContentCreate, category: str, agent: AgentAuth):
    """统一创建内容记录"""
    # 使用 raw SQL 插入 articles 表（Article ORM 在 articles.py 路由中定义）
    result = db.execute(text("""
        INSERT INTO articles (title, category, brand, summary, content, cover_image,
                              video_url, author, tags, status, published_at, created_at, updated_at)
        VALUES (:title, :category, :brand, :summary, :content, :cover_image,
                :video_url, :author, :tags, :status,
                CASE WHEN :status = 'published' THEN NOW() ELSE NULL END,
                NOW(), NOW())
        RETURNING id
    """), {
        "title": body.title,
        "category": category,
        "brand": body.brand or "塔塔",
        "summary": body.summary,
        "content": body.content,
        "cover_image": body.cover_image,
        "video_url": body.video_url,
        "author": body.author or agent.agent_name,
        "tags": body.tags,
        "status": body.status or "draft",
    })
    article_id = result.fetchone()[0]
    db.commit()

    if body.status == "published":
        _emit_event(db, "content.published", {"article_id": article_id, "category": category})

    return _ok({"id": article_id, "category": category}, "内容已创建")


# ══════════════════════════════════════════════════════════════
#  3. 五路 — 组织管理（读写）
# ══════════════════════════════════════════════════════════════

class StaffCreate(BaseModel):
    name: str
    phone: str
    specialty: Optional[str] = None
    company: Optional[str] = None
    level: Optional[str] = "trainee"
    position: Optional[str] = None
    branch_id: Optional[int] = None


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    specialty: Optional[str] = None
    company: Optional[str] = None
    level: Optional[str] = None
    position: Optional[str] = None
    branch_id: Optional[int] = None
    status: Optional[str] = None


@router.get("/org/staff")
def list_staff(
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    keyword: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """员工列表（Consultant = 老师/员工）"""
    q = db.query(Consultant)
    if status:
        q = q.filter(Consultant.status == status)
    if branch_id:
        q = q.filter(Consultant.branch_id == branch_id)
    if keyword:
        q = q.filter(
            (Consultant.name.ilike(f"%{keyword}%")) | (Consultant.phone.ilike(f"%{keyword}%"))
        )
    total = q.count()
    items = q.order_by(Consultant.id).offset(offset).limit(limit).all()
    return _ok({"total": total, "items": [_serialize(c) for c in items]})


@router.post("/org/staff")
def create_staff(
    body: StaffCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """新建员工"""
    exist = db.query(Consultant).filter(Consultant.phone == body.phone).first()
    if exist:
        raise HTTPException(400, f"手机号 {body.phone} 已存在（员工ID: {exist.id}）")

    c = Consultant(
        name=body.name,
        phone=body.phone,
        specialty=body.specialty,
        company=body.company,
        level=body.level,
        position=body.position,
        branch_id=body.branch_id,
        status="active",
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    _emit_event(db, "staff.changed", {"action": "created", "staff_id": c.id, "name": c.name})
    return _ok(_serialize(c), "员工创建成功")


@router.patch("/org/staff/{staff_id}")
def update_staff(
    staff_id: int,
    body: StaffUpdate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """更新员工信息"""
    c = db.query(Consultant).filter(Consultant.id == staff_id).first()
    if not c:
        raise HTTPException(404, "员工不存在")

    changed = []
    for field in ["name", "phone", "specialty", "company", "level", "position", "branch_id", "status"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(c, field, val)
            changed.append(field)
    db.commit()

    _emit_event(db, "staff.changed", {"action": "updated", "staff_id": c.id, "changed_fields": changed})
    return _ok(_serialize(c), "员工信息已更新")


@router.get("/org/staff/{staff_id}/salary")
def get_staff_salary(
    staff_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """查看工资记录"""
    if not year:
        year = date.today().year
    if not month:
        month = date.today().month

    try:
        rows = db.execute(text("""
            SELECT * FROM salary_records
            WHERE consultant_id = :cid AND year = :year AND month = :month
            ORDER BY id DESC
        """), {"cid": staff_id, "year": year, "month": month}).mappings().all()
        return _ok([dict(r) for r in rows])
    except Exception as e:
        return _ok([], f"查询异常: {str(e)}")


@router.post("/org/staff/{staff_id}/disable")
def disable_staff(
    staff_id: int,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """禁用账号"""
    c = db.query(Consultant).filter(Consultant.id == staff_id).first()
    if not c:
        raise HTTPException(404, "员工不存在")
    c.status = "disabled"
    db.commit()

    _emit_event(db, "staff.changed", {"action": "disabled", "staff_id": c.id, "name": c.name})
    return _ok({"id": c.id, "status": "disabled"}, "账号已禁用")


# ══════════════════════════════════════════════════════════════
#  4. 百川 — 财务（只读）
# ══════════════════════════════════════════════════════════════

@router.get("/finance/payments")
def finance_payments(
    pay_status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    member_id: Optional[int] = None,
    consultant_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """查询收款记录"""
    q = db.query(Payment)
    if pay_status:
        q = q.filter(Payment.pay_status == pay_status)
    if member_id:
        q = q.filter(Payment.member_id == member_id)
    if consultant_id:
        q = q.filter(Payment.consultant_id == consultant_id)
    if start_date:
        q = q.filter(Payment.created_at >= start_date)
    if end_date:
        q = q.filter(Payment.created_at <= end_date)
    total = q.count()
    items = q.order_by(desc(Payment.id)).offset(offset).limit(limit).all()
    items_data = [_serialize(p) for p in items]
    _enrich(items_data, db, {"consultant_id": "consultant_name", "member_id": "member_name", "service_id": "service_name"})
    return _ok({"total": total, "items": items_data})


@router.get("/finance/payments/export")
def export_payments_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """导出收款明细CSV"""
    q = db.query(Payment)
    if start_date:
        q = q.filter(Payment.created_at >= start_date)
    if end_date:
        q = q.filter(Payment.created_at <= end_date)
    rows = q.order_by(desc(Payment.id)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "会员ID", "金额", "欠款", "支付方式", "支付类型",
                     "状态", "老师ID", "套餐ID", "服务ID", "支付时间", "创建时间"])
    for p in rows:
        writer.writerow([
            p.id, p.member_id, float(p.amount or 0), float(p.debt_amount or 0),
            p.pay_method, p.pay_type, p.pay_status, p.consultant_id,
            p.package_id, p.service_id,
            p.pay_time.isoformat() if p.pay_time else "",
            p.created_at.isoformat() if p.created_at else "",
        ])
    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=payments_export_{date.today()}.csv"},
    )


@router.get("/finance/summary")
def finance_summary(
    year: Optional[int] = None,
    month: Optional[int] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """财务汇总"""
    if not year:
        year = date.today().year
    if not month:
        month = date.today().month

    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1)
    else:
        last_day = date(year, month + 1, 1)

    # 本月收款汇总
    month_total = float(db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.created_at >= first_day,
        Payment.created_at < last_day,
        Payment.pay_status.in_(["paid", "completed"]),
    ).scalar() or 0)

    # 本月笔数
    month_count = db.query(func.count(Payment.id)).filter(
        Payment.created_at >= first_day,
        Payment.created_at < last_day,
        Payment.pay_status.in_(["paid", "completed"]),
    ).scalar() or 0

    # 本月欠款
    month_debt = float(db.query(func.coalesce(func.sum(Payment.debt_amount), 0)).filter(
        Payment.created_at >= first_day,
        Payment.created_at < last_day,
        Payment.debt_amount > 0,
    ).scalar() or 0)

    # 年度累计
    year_start = date(year, 1, 1)
    year_total = float(db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.created_at >= year_start,
        Payment.created_at < last_day,
        Payment.pay_status.in_(["paid", "completed"]),
    ).scalar() or 0)

    return _ok({
        "year": year,
        "month": month,
        "month_total": month_total,
        "month_count": month_count,
        "month_debt": month_debt,
        "year_total": year_total,
    })


# ══════════════════════════════════════════════════════════════
#  5. 二福 — 数据（只读）
# ══════════════════════════════════════════════════════════════

@router.get("/data/performance")
def data_performance(
    year: Optional[int] = None,
    month: Optional[int] = None,
    consultant_id: Optional[int] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """业绩数据"""
    if not year:
        year = date.today().year
    if not month:
        month = date.today().month

    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1)
    else:
        last_day = date(year, month + 1, 1)

    # 按老师统计回款
    sql = """
        SELECT c.id AS consultant_id, c.name, c.level, c.position,
               COALESCE(SUM(p.amount), 0) AS total_amount,
               COUNT(p.id) AS payment_count
        FROM consultants c
        LEFT JOIN members m ON m.consultant_id = c.id
        LEFT JOIN payments p ON p.member_id = m.id
            AND p.pay_status IN ('paid', 'completed')
            AND p.created_at >= :fd AND p.created_at < :ld
        WHERE c.status = 'active'
    """
    params = {"fd": first_day, "ld": last_day}
    if consultant_id:
        sql += " AND c.id = :cid"
        params["cid"] = consultant_id
    sql += " GROUP BY c.id, c.name, c.level, c.position ORDER BY total_amount DESC"
    q = db.execute(text(sql), params)
    rows = q.mappings().all()

    return _ok({
        "year": year, "month": month,
        "items": [dict(r) for r in rows],
    })


@router.get("/data/orders")
def data_orders(
    year: Optional[int] = None,
    month: Optional[int] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """工单数据统计"""
    if not year:
        year = date.today().year
    if not month:
        month = date.today().month

    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1)
    else:
        last_day = date(year, month + 1, 1)

    # 按状态统计
    stats = db.execute(text("""
        SELECT status, COUNT(*) AS cnt
        FROM service_orders
        WHERE created_at >= :fd AND created_at < :ld
        GROUP BY status
    """), {"fd": first_day, "ld": last_day}).mappings().all()

    # 总数
    total = sum(r["cnt"] for r in stats)

    return _ok({
        "year": year, "month": month,
        "total": total,
        "by_status": {r["status"]: r["cnt"] for r in stats},
    })


@router.get("/data/revenue")
def data_revenue(
    year: Optional[int] = None,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """营收数据（按月汇总）"""
    if not year:
        year = date.today().year

    rows = db.execute(text("""
        SELECT EXTRACT(MONTH FROM created_at)::int AS month,
               COALESCE(SUM(amount), 0) AS total,
               COUNT(*) AS count
        FROM payments
        WHERE EXTRACT(YEAR FROM created_at) = :year
          AND pay_status IN ('paid', 'completed')
        GROUP BY month
        ORDER BY month
    """), {"year": year}).mappings().all()

    return _ok({
        "year": year,
        "monthly": [dict(r) for r in rows],
        "annual_total": sum(float(r["total"]) for r in rows),
    })


@router.get("/data/export")
def data_export(
    type: str = Query("members", description="members/orders/payments"),
    limit: int = Query(1000, le=5000),
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """数据导出CSV"""
    output = io.StringIO()
    writer = csv.writer(output)

    if type == "members":
        writer.writerow(["ID", "姓名", "手机", "编号", "类型", "状态", "城市",
                         "企业", "门店数", "归属老师ID", "创建时间"])
        items = db.query(Member).order_by(desc(Member.id)).limit(limit).all()
        for m in items:
            writer.writerow([m.id, m.name, m.phone, m.member_no, m.member_type,
                             m.status, m.city, m.enterprise_name, m.store_count,
                             m.consultant_id,
                             m.created_at.isoformat() if m.created_at else ""])
    elif type == "orders":
        writer.writerow(["ID", "工单号", "会员ID", "服务ID", "老师ID", "门店",
                         "预约日期", "状态", "评分", "创建时间"])
        items = db.query(ServiceOrder).order_by(desc(ServiceOrder.id)).limit(limit).all()
        for o in items:
            writer.writerow([o.id, o.order_no, o.member_id, o.service_id,
                             o.consultant_id, o.store_name,
                             o.appoint_date.isoformat() if o.appoint_date else "",
                             o.status, o.rating,
                             o.created_at.isoformat() if o.created_at else ""])
    elif type == "payments":
        writer.writerow(["ID", "会员ID", "金额", "方式", "类型", "状态", "创建时间"])
        items = db.query(Payment).order_by(desc(Payment.id)).limit(limit).all()
        for p in items:
            writer.writerow([p.id, p.member_id, float(p.amount or 0),
                             p.pay_method, p.pay_type, p.pay_status,
                             p.created_at.isoformat() if p.created_at else ""])
    else:
        raise HTTPException(400, f"不支持的导出类型: {type}")

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_{type}_{date.today()}.csv"},
    )


# ══════════════════════════════════════════════════════════════
#  6. 九亿 — 服务项目管理（读写）
# ══════════════════════════════════════════════════════════════

class ServiceCreate(BaseModel):
    name: str
    code: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = "塔塔"
    description: Optional[str] = None
    introduction: Optional[str] = None
    service_mode: Optional[str] = "annual"
    total_times: Optional[int] = 5
    duration_days: Optional[int] = 1
    price: Optional[float] = None
    trial_price: Optional[float] = None
    annual_price: Optional[float] = None
    cover_image: Optional[str] = None


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    introduction: Optional[str] = None
    service_mode: Optional[str] = None
    total_times: Optional[int] = None
    duration_days: Optional[int] = None
    price: Optional[float] = None
    trial_price: Optional[float] = None
    annual_price: Optional[float] = None
    cover_image: Optional[str] = None
    status: Optional[str] = None


@router.get("/services")
def list_services(
    status: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """服务项目列表"""
    q = db.query(Service)
    if status:
        q = q.filter(Service.status == status)
    if category:
        q = q.filter(Service.category == category)
    if brand:
        q = q.filter(Service.brand == brand)
    total = q.count()
    items = q.order_by(Service.id).offset(offset).limit(limit).all()
    return _ok({"total": total, "items": [_serialize(s) for s in items]})




@router.get("/services/{service_id}")
def get_service(
    service_id: int,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """单条服务详情"""
    from models.service import Service
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(404, "服务项目不存在")
    return _ok(_serialize(svc))

@router.post("/services")
def create_service(
    body: ServiceCreate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """新增服务项目"""
    # 自动生成编码
    if not body.code:
        count = db.query(func.count(Service.id)).scalar() or 0
        body.code = f"SV-{count + 1:03d}"

    s = Service(
        name=body.name,
        code=body.code,
        category=body.category,
        brand=body.brand or "塔塔",
        description=body.description,
        introduction=body.introduction,
        service_mode=body.service_mode,
        total_times=body.total_times,
        duration_days=body.duration_days,
        price=body.price,
        trial_price=body.trial_price,
        annual_price=body.annual_price,
        cover_image=body.cover_image,
        status="active",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _ok(_serialize(s), "服务项目已创建")


@router.patch("/services/{service_id}")
def update_service(
    service_id: int,
    body: ServiceUpdate,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """更新服务项目"""
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(404, "服务项目不存在")
    for field in ["name", "category", "brand", "description", "introduction",
                  "service_mode", "total_times", "duration_days", "price",
                  "trial_price", "annual_price", "cover_image", "status"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(s, field, val)
    db.commit()
    return _ok(_serialize(s), "服务项目已更新")


@router.post("/services/{service_id}/disable")
def disable_service(
    service_id: int,
    agent: AgentAuth = Depends(_require_write),
    db: DBSession = Depends(get_db),
):
    """下架服务项目"""
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(404, "服务项目不存在")
    s.status = "offline"
    db.commit()
    return _ok({"id": s.id, "status": "offline"}, "服务项目已下架")


@router.get("/dashboard/overview")
def dashboard_overview(
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """全局数据总览"""
    today = date.today()
    first_day_month = date(today.year, today.month, 1)
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)

    # 会员统计
    total_members = db.query(func.count(Member.id)).scalar() or 0
    active_members = db.query(func.count(Member.id)).filter(Member.status == "active").scalar() or 0

    # 工单统计
    total_orders = db.query(func.count(ServiceOrder.id)).scalar() or 0
    month_orders = db.query(func.count(ServiceOrder.id)).filter(
        ServiceOrder.created_at >= first_day_month,
        ServiceOrder.created_at < next_month,
    ).scalar() or 0
    pending_orders = db.query(func.count(ServiceOrder.id)).filter(
        ServiceOrder.status == "pending"
    ).scalar() or 0

    # 收款统计
    month_revenue = float(db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.created_at >= first_day_month,
        Payment.created_at < next_month,
        Payment.pay_status.in_(["paid", "completed"]),
    ).scalar() or 0)

    year_revenue = float(db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.created_at >= date(today.year, 1, 1),
        Payment.pay_status.in_(["paid", "completed"]),
    ).scalar() or 0)

    # 员工统计
    active_staff = db.query(func.count(Consultant.id)).filter(Consultant.status == "active").scalar() or 0

    # 服务统计
    active_services = db.query(func.count(Service.id)).filter(Service.status == "active").scalar() or 0

    return _ok({
        "date": today.isoformat(),
        "members": {
            "total": total_members,
            "active": active_members,
        },
        "orders": {
            "total": total_orders,
            "month": month_orders,
            "pending": pending_orders,
        },
        "revenue": {
            "month": month_revenue,
            "year": year_revenue,
        },
        "staff": {
            "active": active_staff,
        },
        "services": {
            "active": active_services,
        },
    })


# ══════════════════════════════════════════════════════════════
#  7. 司库 — 备份巡检（只读）
# ══════════════════════════════════════════════════════════════

@router.get("/backup/full-export")
def backup_full_export(
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """全量数据导出JSON（司库巡检用）"""
    data = {
        "export_time": datetime.utcnow().isoformat(),
        "agent": agent.agent_id,
    }

    # 各核心表计数 + 样本
    tables = {
        "members": Member,
        "services": Service,
        "service_orders": ServiceOrder,
        "payments": Payment,
    }
    for key, model in tables.items():
        total = db.query(func.count(model.id)).scalar() or 0
        latest = db.query(model).order_by(desc(model.id)).limit(5).all()
        data[key] = {
            "total": total,
            "latest_5": [_serialize(obj) for obj in latest],
        }

    # Consultant
    staff_total = db.query(func.count(Consultant.id)).scalar() or 0
    data["staff"] = {"total": staff_total}

    # Webhook events
    event_total = db.query(func.count(WebhookEvent.id)).scalar() or 0
    pending_events = db.query(func.count(WebhookEvent.id)).filter(WebhookEvent.status == "pending").scalar() or 0
    data["webhook_events"] = {"total": event_total, "pending": pending_events}

    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=full_export_{date.today()}.json"},
    )


@router.get("/audit-logs")
def audit_logs(
    days: int = Query(30, le=90),
    limit: int = Query(200, le=1000),
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """操作日志"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    try:
        rows = db.execute(text(
            "SELECT id, admin_id, action, target_type, target_id, detail, created_at "
            "FROM operation_logs WHERE created_at >= :cutoff ORDER BY id DESC LIMIT :lim"
        ), {"cutoff": cutoff, "lim": limit}).mappings().all()
        return _ok([dict(r) for r in rows])
    except Exception:
        # operation_logs 表可能不存在
        return _ok([], "operation_logs 表暂未创建")


# ══════════════════════════════════════════════════════════════
#  事件辅助
# ══════════════════════════════════════════════════════════════

def _emit_event(db: DBSession, event_type: str, payload: dict):
    """发射事件到 webhook_events 表"""
    try:
        from models.webhook_event import emit_event, EVENT_ROUTING
        emit_event(db, event_type, payload)
    except Exception as e:
        logger.warning(f"[AGENT_API] emit_event failed: {e}")

# ══════════════════════════════════════════════════════════════
#  采购+储值 只读接口（百川财务系统拉数用）— 2026-06-02
# ══════════════════════════════════════════════════════════════

@router.get("/purchases")
def agent_purchases(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    branch_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = Query(200, le=500),
    offset: int = 0,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """采购/支出记录列表（财务系统拉进项+期间费用）"""
    from models.purchase import Purchase
    q = db.query(Purchase)
    if branch_id:
        q = q.filter(Purchase.branch_id == branch_id)
    if category:
        q = q.filter(Purchase.category == category)
    if start_date:
        q = q.filter(Purchase.purchase_date >= start_date)
    if end_date:
        q = q.filter(Purchase.purchase_date <= end_date)
    total = q.count()
    items = q.order_by(desc(Purchase.purchase_date), desc(Purchase.id)).offset(offset).limit(limit).all()
    out = []
    for p in items:
        out.append({
            "id": p.id, "branch_id": p.branch_id,
            "supplier": p.supplier, "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None,
            "item": p.item, "qty": float(p.qty or 0),
            "amount": float(p.amount or 0), "tax_amount": float(p.tax_amount or 0),
            "invoice_no": p.invoice_no, "category": p.category,
            "pay_method": p.pay_method, "has_invoice": p.has_invoice,
            "remark": p.remark,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return _ok({"total": total, "items": out})


@router.get("/recharges")
def agent_recharges(
    member_id: Optional[int] = None,
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    limit: int = Query(200, le=500),
    offset: int = 0,
    agent: AgentAuth = Depends(_require_agent),
    db: DBSession = Depends(get_db),
):
    """储值记录列表（财务系统拉预收款负债）"""
    from models.recharge import Recharge
    q = db.query(Recharge)
    if member_id:
        q = q.filter(Recharge.member_id == member_id)
    if status:
        q = q.filter(Recharge.status == status)
    if branch_id:
        q = q.filter(Recharge.branch_id == branch_id)
    total = q.count()
    items = q.order_by(desc(Recharge.id)).offset(offset).limit(limit).all()
    out = []
    for r in items:
        out.append({
            "id": r.id, "member_id": r.member_id,
            "consultant_id": r.consultant_id, "branch_id": r.branch_id,
            "title": r.title,
            "total_amount": float(r.total_amount or 0),
            "total_count": r.total_count, "used_count": r.used_count,
            "remaining_count": r.remaining_count,
            "unit_price": float(r.unit_price or 0),
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "expire_date": r.expire_date.isoformat() if r.expire_date else None,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return _ok({"total": total, "items": out})

