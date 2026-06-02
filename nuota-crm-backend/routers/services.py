# 专案服务路由 —— 小程序端 + 管理端
# 2026-05-14 v2: 按九哥修改意见重构工单流程
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List
import json as json_mod

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from utils.auth import get_current_admin_or_consultant
from utils.helpers import ok
from models import (
    Service, ServicePackage, ServiceOrder, ServiceWorkLog,
    Member, Consultant, Payment
)


# ══════════════════ Schemas ══════════════════

class ServiceOut(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = "塔塔"
    description: Optional[str] = None
    service_mode: Optional[str] = "annual"
    total_times: Optional[int] = 5
    visit_days: Optional[int] = 2
    duration_days: int = 1
    price: Optional[float] = None
    annual_price: Optional[float] = None
    cover_image: Optional[str] = None
    status: str
    class Config:
        from_attributes = True

class ServiceCreate(BaseModel):
    name: str
    code: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = "塔塔"
    description: Optional[str] = None
    service_mode: Optional[str] = "annual"
    total_times: Optional[int] = 5
    duration_days: Optional[int] = 2
    price: Optional[Decimal] = None
    annual_price: Optional[Decimal] = None
    cover_image: Optional[str] = None

class PackageOut(BaseModel):
    id: int
    member_id: int
    package_no: Optional[str] = None
    total_times: int
    used_times: int
    amount: Optional[float] = None
    start_date: Optional[date] = None
    expire_date: Optional[date] = None
    status: str
    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    member_id: int
    service_id: int
    appoint_date: date
    appoint_time: str
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    consultant_id: Optional[int] = None
    remark: Optional[str] = None

class OrderOut(BaseModel):
    id: int
    order_no: Optional[str] = None
    member_id: Optional[int] = None
    service_id: Optional[int] = None
    consultant_id: Optional[int] = None
    assistant_id: Optional[int] = None
    store_name: Optional[str] = None
    appoint_date: Optional[date] = None
    appoint_time: Optional[str] = None
    status: str
    workflow_stage: Optional[str] = None
    workflow_progress: int = 0
    rating: Optional[int] = None
    # 关联名称（手动填充）
    service_name: Optional[str] = None
    consultant_name: Optional[str] = None
    member_name: Optional[str] = None
    class Config:
        from_attributes = True

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    workflow_stage: Optional[str] = None
    workflow_progress: Optional[int] = None
    member_id: Optional[int] = None
    service_id: Optional[int] = None
    consultant_id: Optional[int] = None
    assistant_id: Optional[int] = None
    appoint_date: Optional[date] = None
    appoint_time: Optional[str] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    visit_number: Optional[int] = None
    remark: Optional[str] = None

# ── Step 1: 管理员确认 ──
class OrderConfirmIn(BaseModel):
    consultant_id: int                          # 主案老师
    assistant_id: Optional[int] = None          # 助理老师（可空）
    appoint_date: Optional[date] = None
    appoint_time: Optional[str] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    remark: Optional[str] = None

# ── Step 2: 老师接单 ──
class OrderAcceptIn(BaseModel):
    accept_note: Optional[str] = None  # 接单备注

# ── Step 3: 执案准备（塔塔五关Checklist + 订票信息） ──
class OrderPrepareIn(BaseModel):
    prepare_summary: str               # 准备事项摘要
    checklist: Optional[str] = None    # JSON: 五关Checklist
    travel_info: Optional[str] = None  # 订票信息（航班/高铁/酒店）
    materials: Optional[str] = None    # 准备的资料/文件

# ── Step 4: 到店开始执案 ──
class OrderStartIn(BaseModel):
    actual_start_date: Optional[date] = None
    participants: Optional[str] = None  # 参与人员
    agenda: Optional[str] = None        # 研讨会议程

# ── Step 5: 每日执案日志 ──
class OrderDayLogIn(BaseModel):
    day_number: int = 1
    stage: str
    content: str
    findings: Optional[str] = None
    decisions: Optional[str] = None
    images: Optional[str] = None
    next_actions: Optional[str] = None

# ── Step 6: 提交执案报告（含文件上传） ──
class OrderReportIn(BaseModel):
    summary: str                                # 执案总结
    problems_found: Optional[str] = None        # 核心问题
    solutions_built: Optional[str] = None       # 搭建方案
    follow_up_plan: Optional[str] = None        # 后续跟进计划
    next_visit_suggestion: Optional[str] = None # 建议下次下店时间
    meeting_records: Optional[str] = None       # 会议记录文件 JSON（URL列表）
    deliverables: Optional[str] = None          # 交付给客户的方案文件 JSON（URL列表）
    attachments: Optional[str] = None           # 其他附件 JSON

# ── Step 7: 执案后跟进（2-3次回访会议） ──
class FollowUpMeetingIn(BaseModel):
    meeting_number: int = 1                     # 第几次跟进会议
    meeting_date: Optional[date] = None         # 会议日期
    meeting_type: str = "online"                # online线上 / onsite线下
    content: str                                # 会议内容
    data_review: Optional[str] = None           # 执案数据回顾（如业绩对比、指标变化）
    issues: Optional[str] = None                # 发现的新问题
    actions: Optional[str] = None               # 跟进行动项
    meeting_record_file: Optional[str] = None   # 会议记录文件URL
    images: Optional[str] = None                # 图片URL JSON

# ── 通用 ──
class WorkLogCreate(BaseModel):
    stage: str
    content: str
    images: Optional[str] = None
    consultant_id: Optional[int] = None
    day_number: Optional[int] = None
    findings: Optional[str] = None
    decisions: Optional[str] = None
    next_actions: Optional[str] = None
    log_type: Optional[str] = 'note'

class RatingSubmit(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


# ══════════════════ 小程序端路由 ══════════════════

router = APIRouter(prefix="/api/v1/services", tags=["专案服务-小程序端"])

@router.get("")
def list_services(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Service).filter(Service.status == "active")
    if category:
        q = q.filter(Service.category == category)
    items = q.order_by(Service.id).all()
    # 查所有活跃老师及其 service_modules
    import json as _json
    consultants = db.query(Consultant).filter(Consultant.status == "active").all()
    consultant_map = {}  # service_id -> [consultant_info]
    for c in consultants:
        try:
            modules = _json.loads(c.service_modules) if c.service_modules else []
        except:
            modules = []
        for sid in modules:
            consultant_map.setdefault(sid, []).append({
                "id": c.id,
                "name": c.name,
                "specialty": c.specialty or "",
                "level": c.level or "",
                "avatar": c.avatar or "",
            })
    result = []
    for s in items:
        d = ServiceOut.from_orm(s).dict()
        d["consultants"] = consultant_map.get(s.id, [])
        result.append(d)
    return ok(result)


@router.get("/grouped")
def grouped_services(member_id: int, category: Optional[str] = None, db: Session = Depends(get_db)):
    """按已合作/未合作分组返回服务列表"""
    q = db.query(Service).filter(Service.status == "active")
    if category:
        q = q.filter(Service.category == category)
    all_services = q.order_by(Service.id).all()

    # 查该会员有工单的服务ID
    ordered_svc_ids = set(
        r[0] for r in db.query(ServiceOrder.service_id)
        .filter(ServiceOrder.member_id == member_id)
        .distinct()
        .all()
    )

    contracted = []
    available = []
    for s in all_services:
        d = ServiceOut.from_orm(s).dict()
        # 查该服务最新工单
        latest = db.query(ServiceOrder).filter(
            ServiceOrder.member_id == member_id,
            ServiceOrder.service_id == s.id
        ).order_by(ServiceOrder.created_at.desc()).first()
        if latest:
            d['latest_order'] = _enrich_order(latest, db)
            contracted.append(d)
        else:
            available.append(d)

    return ok({"contracted": contracted, "available": available})

def _enrich_order(o, db):
    """给工单填充关联名称"""
    d = OrderOut.from_orm(o).dict()
    if o.service_id:
        svc = db.query(Service).filter(Service.id == o.service_id).first()
        if svc:
            d['service_name'] = svc.name
    if o.consultant_id:
        c = db.query(Consultant).filter(Consultant.id == o.consultant_id).first()
        if c:
            d['consultant_name'] = c.name
    if o.member_id:
        m = db.query(Member).filter(Member.id == o.member_id).first()
        if m:
            d['member_name'] = m.name
    return d

@router.get("/{service_id}")
def get_service(service_id: int, db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(404, "服务不存在")
    return ok(ServiceOut.from_orm(s).dict())

@router.get("/packages/my")
def my_packages(member_id: int, db: Session = Depends(get_db)):
    items = db.query(ServicePackage).filter(
        ServicePackage.member_id == member_id,
        ServicePackage.status == "active"
    ).all()
    return ok([PackageOut.from_orm(p).dict() for p in items])

@router.post("/orders")
def create_order(body: OrderCreate, db: Session = Depends(get_db)):
    """会员预约专案服务 → 生成工单"""
    member = db.query(Member).filter(Member.id == body.member_id).first()
    if not member:
        raise HTTPException(404, "会员不存在")
    if not member.agreement_signed:
        raise HTTPException(400, "请先完成协议签约")

    pkg = db.query(ServicePackage).filter(
        ServicePackage.member_id == body.member_id,
        ServicePackage.status == "active",
        ServicePackage.used_times < ServicePackage.total_times,
    ).first()

    service = db.query(Service).filter(Service.id == body.service_id).first()
    if not service:
        raise HTTPException(404, "服务不存在")

    order_no = f"SO-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
    order = ServiceOrder(
        order_no=order_no,
        member_id=body.member_id,
        service_id=body.service_id,
        package_id=pkg.id if pkg else None,
        consultant_id=body.consultant_id,
        store_name=body.store_name,
        store_address=body.store_address,
        appoint_date=body.appoint_date,
        appoint_time=body.appoint_time,
        status="pending",
        workflow_stage="待确认",
        workflow_progress=5,
        remark=body.remark,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    if body.consultant_id:
        from routers.notifications import push_notification
        from models.booking import Consultant
        consultant = db.query(Consultant).filter(Consultant.id == body.consultant_id).first()
        if consultant:
            push_notification(
                db, recipient_type="consultant", recipient_id=consultant.id,
                title=f"新工单已分配给你 · {service.name}",
                body=f"客户：{member.name if member else ''}，预约日期：{body.appoint_date or '待确认'}，工单号：{order_no}",
                ntype="order", ref_type="service_order", ref_id=order.id,
            )
            db.commit()
    return ok(_enrich_order(order, db))

@router.get("/orders/my")
def my_orders(member_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ServiceOrder).filter(ServiceOrder.member_id == member_id)
    if status:
        q = q.filter(ServiceOrder.status == status)
    items = q.order_by(ServiceOrder.created_at.desc()).all()
    return ok([_enrich_order(o, db) for o in items])

@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    return ok(_enrich_order(o, db))

@router.post("/orders/{order_id}/rating")
def submit_rating(order_id: int, body: RatingSubmit, db: Session = Depends(get_db)):
    """会员提交满意度评价（整体执案结束后）"""
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status not in ("follow_up", "completed"):
        raise HTTPException(400, "服务尚未进入跟进/完成阶段，无法评价")
    o.rating = body.rating
    o.rating_comment = body.comment
    o.rated_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "评价成功"}


# ══════════════════ 管理端路由 ══════════════════

admin_router = APIRouter(prefix="/admin/services", tags=["专案服务-管理端"])

@admin_router.get("", response_model=List[ServiceOut])
def admin_list_services(db: Session = Depends(get_db)):
    return db.query(Service).order_by(Service.id).all()

@admin_router.post("", response_model=ServiceOut)
def admin_create_service(body: ServiceCreate, db: Session = Depends(get_db)):
    s = Service(**body.dict())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@admin_router.put("/{service_id}", response_model=ServiceOut)
def admin_update_service(service_id: int, body: ServiceCreate, db: Session = Depends(get_db)):
    import json
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(404, "服务不存在")
    old_name = s.name
    for k, v in body.dict(exclude_none=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    if old_name != s.name:
        consultants = db.query(Consultant).all()
        for c in consultants:
            if c.service_modules:
                try:
                    modules = json.loads(c.service_modules)
                    if old_name in modules:
                        modules = [s.name if m == old_name else m for m in modules]
                        c.service_modules = json.dumps(modules, ensure_ascii=False)
                except Exception:
                    pass
        db.commit()
    return s


@admin_router.delete("/{service_id}")
def admin_delete_service(service_id: int, db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(404, "服务不存在")
    # 检查是否有关联工单
    order_count = db.query(ServiceOrder).filter(ServiceOrder.service_id == service_id).count()
    if order_count > 0:
        # 有工单关联，改为下架而不是删除
        s.status = "offline"
        db.commit()
        return {"code": 0, "msg": f"该服务已有{order_count}条工单，已转为下架"}
    db.delete(s)
    db.commit()
    return {"code": 0, "msg": "已删除"}


@admin_router.put("/{service_id}/toggle")
def admin_toggle_service(service_id: int, db: Session = Depends(get_db)):
    s = db.query(Service).filter(Service.id == service_id).first()
    if not s:
        raise HTTPException(404, "服务不存在")
    s.status = "offline" if s.status == "active" else "active"
    db.commit()
    label = "下架" if s.status == "offline" else "上架"
    return {"code": 0, "msg": f"已{label}", "status": s.status}

@admin_router.get("/orders", response_model=List[OrderOut])
def admin_list_orders(
    status: Optional[str] = None,
    consultant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    q = db.query(ServiceOrder)
    if current_user.is_consultant:
        q = q.filter(ServiceOrder.consultant_id == current_user.consultant_id)
    elif consultant_id:
        q = q.filter(ServiceOrder.consultant_id == consultant_id)
    if status:
        q = q.filter(ServiceOrder.status == status)
    return q.order_by(ServiceOrder.created_at.desc()).limit(100).all()

@admin_router.put("/orders/{order_id}", response_model=OrderOut)
def admin_update_order(order_id: int, body: OrderUpdate, db: Session = Depends(get_db)):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    for k, v in body.dict(exclude_none=True).items():
        setattr(o, k, v)
    if body.status == "completed" and o.package_id:
        pkg = db.query(ServicePackage).filter(ServicePackage.id == o.package_id).first()
        if pkg and pkg.used_times < pkg.total_times:
            pkg.used_times += 1
    db.commit()
    db.refresh(o)
    return o

@admin_router.post("/orders/{order_id}/work-logs")
def admin_add_work_log(order_id: int, body: WorkLogCreate, db: Session = Depends(get_db)):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    log = _add_log(
        db, order_id, body.stage, body.content,
        images=body.images, consultant_id=body.consultant_id,
        day_number=body.day_number, findings=body.findings,
        decisions=body.decisions, next_actions=body.next_actions,
        log_type=body.log_type or 'note',
    )
    o.workflow_stage = body.stage
    db.commit()
    return {"code": 0, "msg": "日志添加成功", "data": {"id": log.id}}

@admin_router.get("/orders/{order_id}/work-logs")
def admin_list_work_logs(order_id: int, db: Session = Depends(get_db)):
    logs = db.query(ServiceWorkLog).filter(
        ServiceWorkLog.order_id == order_id
    ).order_by(ServiceWorkLog.created_at).all()
    return {"code": 0, "data": [
        {
            "id": l.id, "stage": l.stage, "content": l.content,
            "images": l.images, "day_number": l.day_number,
            "findings": l.findings, "decisions": l.decisions,
            "next_actions": l.next_actions, "log_type": l.log_type,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        } for l in logs
    ]}

@admin_router.post("/packages")
def admin_create_package(
    member_id: int, total_times: int, amount: Decimal,
    start_date: date, expire_date: date, db: Session = Depends(get_db),
):
    pkg_no = f"PKG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pkg = ServicePackage(
        member_id=member_id, package_no=pkg_no,
        total_times=total_times, amount=amount,
        start_date=start_date, expire_date=expire_date, status="active",
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return {"code": 0, "msg": "套餐开通成功", "data": {"id": pkg.id, "package_no": pkg_no}}


# ════════════════════════════════════════════════════════════
# 🔄 工单流程引擎 v2 —— 塔塔专案服务全链路
# ════════════════════════════════════════════════════════════
#
# 状态机（8步，新增 follow_up 跟进阶段）：
#
# pending(待确认) → confirmed(已确认) → accepted(已接单)
# → preparing(执案准备) → in_progress(执案中) → reporting(提交报告)
# → follow_up(执案后跟进) → completed(整体结束) / cancelled(已取消)
#
# 核心改动（v2 vs v1）：
#
# 1. 接单通知 → 通知该会员的**销售老师**（非会员本人）
# 2. 执案准备 → 塔塔五关Checklist（对接/材料/现场/协作/收尾）+ 订票信息
# 3. 执案报告 → 新增会议记录文件 + 客户方案文件上传
# 4. 新增 follow_up 阶段 → 后续2-3次跟进会议，每次填会议记录+执案数据
# 5. 整体执案结束 → 管理员审核 + 会员评价 + 扣减套餐
# ════════════════════════════════════════════════════════════

WORKFLOW_STEPS = [
    {"status": "pending",      "stage": "待确认",       "progress": 5,   "label": "待确认",        "actor": "admin"},
    {"status": "confirmed",    "stage": "已确认",       "progress": 12,  "label": "已确认",        "actor": "admin"},
    {"status": "accepted",     "stage": "已接单",       "progress": 20,  "label": "老师已接单",     "actor": "consultant"},
    {"status": "preparing",    "stage": "执案准备",     "progress": 35,  "label": "执案准备",      "actor": "consultant"},
    {"status": "in_progress",  "stage": "执案中",       "progress": 50,  "label": "研讨会执案中",   "actor": "consultant"},
    {"status": "reporting",    "stage": "提交报告",     "progress": 70,  "label": "已提交报告",     "actor": "consultant"},
    {"status": "follow_up",    "stage": "执案后跟进",   "progress": 85,  "label": "跟进中(2-3次)",  "actor": "consultant"},
    {"status": "completed",    "stage": "整体结束",     "progress": 100, "label": "整体执案结束",   "actor": "admin"},
]

STATUS_INDEX = {s["status"]: i for i, s in enumerate(WORKFLOW_STEPS)}

# 塔塔执案前五关Checklist模板
TATA_CHECKLIST_TEMPLATE = [
    # 第一关：对接确认（出发前3天）
    {"gate": 1, "gate_name": "对接确认（出发前3天）", "item": "已联系带队老师，确认到达时间和地点", "done": False},
    {"gate": 1, "gate_name": "对接确认（出发前3天）", "item": "已明确本次执案自己的具体职责（逐条列出）", "done": False},
    {"gate": 1, "gate_name": "对接确认（出发前3天）", "item": "已知道本次执案的核心目标是什么", "done": False},
    {"gate": 1, "gate_name": "对接确认（出发前3天）", "item": "已了解客户基本情况（门店规模/老板姓名/上次执案遗留问题）", "done": False},
    # 第二关：材料准备（出发前1天）
    {"gate": 2, "gate_name": "材料准备（出发前1天）", "item": "会议记录模板已准备好（不是到了再找）", "done": False},
    {"gate": 2, "gate_name": "材料准备（出发前1天）", "item": "执案日程表已收到并读完", "done": False},
    {"gate": 2, "gate_name": "材料准备（出发前1天）", "item": "团队行程已同步（谁几点到/住哪个酒店/怎么集合）", "done": False},
    {"gate": 2, "gate_name": "材料准备（出发前1天）", "item": "自己的住宿已确认", "done": False},
    # 第三关：现场规范（执案当天）
    {"gate": 3, "gate_name": "现场规范（执案当天）", "item": "到店第一件事：找带队老师报到，确认今天任务分工", "done": False},
    {"gate": 3, "gate_name": "现场规范（执案当天）", "item": "会议记录当场记，当天整理完发带队老师审核", "done": False},
    {"gate": 3, "gate_name": "现场规范（执案当天）", "item": "文案/输出物当天完成，不过夜", "done": False},
    {"gate": 3, "gate_name": "现场规范（执案当天）", "item": "有不懂的当场问，不猜，不扛", "done": False},
    # 第四关：团队协作（全程）
    {"gate": 4, "gate_name": "团队协作（全程）", "item": "有集体动作（敬酒/发言/表态）前先跟团队沟通，不单独行动", "done": False},
    {"gate": 4, "gate_name": "团队协作（全程）", "item": "团队所有人行程变化第一时间同步群里", "done": False},
    {"gate": 4, "gate_name": "团队协作（全程）", "item": "客户面前展示统一形象，有分歧私下解决", "done": False},
    # 第五关：收尾（执案结束当天）
    {"gate": 5, "gate_name": "收尾（执案结束当天）", "item": "会议记录已发带队老师", "done": False},
    {"gate": 5, "gate_name": "收尾（执案结束当天）", "item": "执案总结已完成（不少于300字，当天发）", "done": False},
    {"gate": 5, "gate_name": "收尾（执案结束当天）", "item": "下次执案待解决问题已记录", "done": False},
    {"gate": 5, "gate_name": "收尾（执案结束当天）", "item": "已向带队老师确认下次执案时间", "done": False},
]


def _push_notif(db, recipient_type, recipient_id, title, body, ntype="order", ref_type="service_order", ref_id=None):
    from routers.notifications import push_notification
    push_notification(db, recipient_type, recipient_id, title, body, ntype, ref_type, ref_id)

def _push_admins(db, title, body, ntype="order", ref_type="service_order", ref_id=None):
    from routers.notifications import push_to_all_admins
    push_to_all_admins(db, title, body, ntype, ref_type, ref_id)


# ────────── 流程查询 ──────────

@admin_router.get("/orders/{order_id}/workflow")
def get_workflow(
    order_id: int, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    """获取工单完整流程状态"""
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")

    current_idx = STATUS_INDEX.get(o.status, 0)

    logs = db.query(ServiceWorkLog).filter(
        ServiceWorkLog.order_id == order_id
    ).order_by(ServiceWorkLog.created_at).all()

    member = db.query(Member).filter(Member.id == o.member_id).first() if o.member_id else None
    service = db.query(Service).filter(Service.id == o.service_id).first() if o.service_id else None
    consultant = db.query(Consultant).filter(Consultant.id == o.consultant_id).first() if o.consultant_id else None
    assistant = db.query(Consultant).filter(Consultant.id == o.assistant_id).first() if o.assistant_id else None

    # 查询关联排期（计算实际服务天数）
    schedules = db.query(ConsultantSchedule).filter(
        ConsultantSchedule.order_id == order_id
    ).order_by(ConsultantSchedule.schedule_date).all()
    schedule_days = len(set(s.schedule_date for s in schedules))
    schedule_start = str(min(s.schedule_date for s in schedules)) if schedules else None
    schedule_end = str(max(s.schedule_date for s in schedules)) if schedules else None

    # 跟进会议统计
    followup_logs = [l for l in logs if l.log_type == 'followup']
    followup_count = len(followup_logs)

    return {"code": 0, "data": {
        "order": {
            "id": o.id,
            "order_no": o.order_no,
            "member_id": o.member_id,
            "service_id": o.service_id,
            "consultant_id": o.consultant_id,
            "assistant_id": o.assistant_id,
            "status": o.status,
            "workflow_stage": o.workflow_stage,
            "workflow_progress": o.workflow_progress or 0,
            "appoint_date": str(o.appoint_date) if o.appoint_date else None,
            "appoint_time": o.appoint_time,
            "store_name": o.store_name,
            "store_address": o.store_address,
            "visit_number": o.visit_number,
            "remark": o.remark,
            "rating": o.rating,
            "rating_comment": o.rating_comment,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        },
        "member": {
            "id": member.id, "name": member.name, "phone": member.phone,
            "enterprise_name": member.enterprise_name,
        } if member else None,
        "service": {
            "id": service.id, "name": service.name, "category": service.category,
            "duration_days": service.duration_days,
        } if service else None,
        "consultant": {
            "id": consultant.id, "name": consultant.name, "phone": consultant.phone,
            "specialty": consultant.specialty, "role": "主案老师",
        } if consultant else None,
        "assistant": {
            "id": assistant.id, "name": assistant.name, "phone": assistant.phone,
            "specialty": assistant.specialty, "role": "助理老师",
        } if assistant else None,
        "steps": [
            {**s, "current": i == current_idx, "done": i < current_idx}
            for i, s in enumerate(WORKFLOW_STEPS)
        ],
        "logs": [{
            "id": l.id, "stage": l.stage, "content": l.content,
            "images": l.images, "day_number": l.day_number,
            "findings": l.findings, "decisions": l.decisions,
            "next_actions": l.next_actions, "log_type": l.log_type,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        } for l in logs],
        "followup_count": followup_count,
        "schedule_days": schedule_days,
        "schedule_start": schedule_start,
        "schedule_end": schedule_end,
        "checklist_template": TATA_CHECKLIST_TEMPLATE,
        "can_advance": _can_advance(o, current_user),
    }}


def _can_advance(order, current_user) -> dict:
    s = order.status
    is_admin = not current_user.is_consultant
    is_own = current_user.is_consultant and current_user.consultant_id == order.consultant_id
    return {
        "can_confirm":    s == "pending"      and is_admin,
        "can_accept":     s == "confirmed"    and (is_own or is_admin),
        "can_prepare":    s == "accepted"     and (is_own or is_admin),
        "can_start":      s == "preparing"    and (is_own or is_admin),
        "can_log":        s == "in_progress"  and (is_own or is_admin),
        "can_report":     s == "in_progress"  and (is_own or is_admin),
        "can_followup":   s == "follow_up"    and (is_own or is_admin),
        "can_complete":   s == "follow_up"    and is_admin,
        "can_cancel":     s not in ("completed", "cancelled") and is_admin,
    }


# ────────── Step 1: 管理员确认 ──────────

@admin_router.put("/orders/{order_id}/confirm")
def workflow_confirm(
    order_id: int, body: OrderConfirmIn, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status != "pending":
        raise HTTPException(400, f"当前状态({o.status})不可确认")

    c = db.query(Consultant).filter(Consultant.id == body.consultant_id).first()
    if not c:
        raise HTTPException(404, "老师不存在")

    o.consultant_id = body.consultant_id
    if body.assistant_id:
        o.assistant_id = body.assistant_id
    if body.appoint_date:
        o.appoint_date = body.appoint_date
    if body.appoint_time:
        o.appoint_time = body.appoint_time
    if body.store_name:
        o.store_name = body.store_name
    if body.store_address:
        o.store_address = body.store_address
    if body.remark:
        o.remark = body.remark
    o.status = "confirmed"
    o.workflow_stage = "已确认·等待老师接单"
    o.workflow_progress = 12

    # 助理老师信息
    asst = db.query(Consultant).filter(Consultant.id == body.assistant_id).first() if body.assistant_id else None
    asst_msg = f"，助理老师：{asst.name}" if asst else ""

    member = db.query(Member).filter(Member.id == o.member_id).first()
    _add_log(db, order_id, "系统", f"工单已确认，主案老师：{c.name}{asst_msg}，预约日期：{o.appoint_date}", log_type="system")

    # 通知主案老师
    _push_notif(db, "consultant", c.id,
        f"新工单已分配给你（主案）",
        f"客户：{member.name if member else ''}，服务：{o.store_name or ''}，日期：{o.appoint_date}",
        ref_id=o.id)

    # 通知助理老师
    if asst:
        _push_notif(db, "consultant", asst.id,
            f"新工单已分配给你（助理）",
            f"主案老师：{c.name}，客户：{member.name if member else ''}，日期：{o.appoint_date}",
            ref_id=o.id)

    db.commit()
    return {"code": 0, "msg": "工单已确认，已通知老师"}


# ────────── Step 2: 老师接单 → 通知该会员的销售老师 ──────────

@admin_router.put("/orders/{order_id}/accept")
def workflow_accept(
    order_id: int, body: OrderAcceptIn, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status != "confirmed":
        raise HTTPException(400, f"当前状态({o.status})不可接单")
    if current_user.is_consultant and current_user.consultant_id != o.consultant_id:
        raise HTTPException(403, "只能接受分配给自己的工单")

    o.status = "accepted"
    o.workflow_stage = "已接单·准备执案资料"
    o.workflow_progress = 20

    note = body.accept_note or "已确认接单"
    c = db.query(Consultant).filter(Consultant.id == o.consultant_id).first()
    _add_log(db, order_id, "接单", f"老师已接单：{note}", log_type="system")

    # 通知管理员
    _push_admins(db, f"{c.name if c else '老师'}已接单 {o.order_no}",
                 f"接单备注：{note}", ref_id=o.id)

    # ★ 通知1：该会员的销售老师
    member = db.query(Member).filter(Member.id == o.member_id).first()
    if member and member.consultant_id:
        sales_consultant = db.query(Consultant).filter(Consultant.id == member.consultant_id).first()
        if sales_consultant:
            _push_notif(db, "consultant", sales_consultant.id,
                f"你的客户 {member.name} 的工单已被 {c.name if c else '老师'} 接单",
                f"工单号：{o.order_no}，服务：{o.store_name or ''}",
                ref_id=o.id)
            from services.notify_service import send_wecom
            send_wecom(f"📋 销售通知：你的客户 {member.name} 的专案工单 {o.order_no} 已由 {c.name if c else '老师'} 接单。")

    # ★ 通知2：会员本人（小程序站内通知，老师会回电确认）
    if member:
        _push_notif(db, "member", member.id,
            f"您的专案服务已有老师接单",
            f"{c.name if c else '老师'}老师已接受您的专案工单（{o.order_no}），老师将与您电话确认具体安排。",
            ref_id=o.id)

    db.commit()
    return {"code": 0, "msg": "接单成功，已通知销售老师和会员"}


# ────────── Step 3: 执案准备（五关Checklist + 订票信息） ──────────

@admin_router.put("/orders/{order_id}/prepare")
def workflow_prepare(
    order_id: int, body: OrderPrepareIn, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status != "accepted":
        raise HTTPException(400, f"当前状态({o.status})不可提交准备")

    o.status = "preparing"
    o.workflow_stage = "执案准备中"
    o.workflow_progress = 35

    content_parts = [f"准备摘要：{body.prepare_summary}"]
    if body.travel_info:
        content_parts.append(f"🚄 订票信息：{body.travel_info}")
    if body.checklist:
        content_parts.append(f"📋 五关Checklist：{body.checklist}")
    if body.materials:
        content_parts.append(f"📎 资料：{body.materials}")

    _add_log(db, order_id, "执案准备", "\n".join(content_parts), log_type="prepare")

    _push_admins(db, f"工单 {o.order_no} 执案准备已提交",
                 f"{body.prepare_summary[:100]}", ref_id=o.id)

    db.commit()
    return {"code": 0, "msg": "执案准备已提交（含五关Checklist + 订票信息）"}


# ── 获取五关Checklist模板 ──

@admin_router.get("/checklist-template")
def get_checklist_template():
    """返回塔塔执案前五关Checklist模板"""
    return {"code": 0, "data": TATA_CHECKLIST_TEMPLATE}


# ────────── Step 4: 开始执案（到店） ──────────

@admin_router.put("/orders/{order_id}/start")
def workflow_start(
    order_id: int, body: OrderStartIn, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status != "preparing":
        raise HTTPException(400, f"当前状态({o.status})不可开始执案")

    actual_date = body.actual_start_date or date.today()
    o.status = "in_progress"
    o.workflow_stage = "研讨会执案中 · Day1"
    o.workflow_progress = 50

    parts = [f"执案正式开始，实际到店日期：{actual_date}"]
    if body.participants:
        parts.append(f"参与人员：{body.participants}")
    if body.agenda:
        parts.append(f"研讨会议程：{body.agenda}")
    _add_log(db, order_id, "开始执案", "\n".join(parts), log_type="system")

    # 自动创建排期
    service = db.query(Service).filter(Service.id == o.service_id).first() if o.service_id else None
    duration = service.duration_days if service and service.duration_days else 2
    member = db.query(Member).filter(Member.id == o.member_id).first() if o.member_id else None
    title = member.enterprise_name or member.name or '' if member else ''

    from models.booking import ConsultantSchedule
    # 主案老师 + 助理老师都创建排期
    consultant_ids = [o.consultant_id]
    if o.assistant_id:
        consultant_ids.append(o.assistant_id)
    for cid in consultant_ids:
        if not cid:
            continue
        for i in range(duration):
            d = actual_date + timedelta(days=i)
            exists = db.query(ConsultantSchedule).filter(
                ConsultantSchedule.consultant_id == cid,
                ConsultantSchedule.schedule_date == d,
            ).first()
            if not exists:
                db.add(ConsultantSchedule(
                    consultant_id=cid, schedule_date=d,
                    city=o.store_name or '', schedule_type='busy', title=title,
                    remark=f'专案工单#{o.id} 自动排期',
                    order_id=o.id,
                    created_by=current_user.user_id if hasattr(current_user, 'user_id') else None,
                ))
            elif not exists.order_id:
                exists.order_id = o.id  # 关联已有排期到工单

    c = db.query(Consultant).filter(Consultant.id == o.consultant_id).first()
    _push_admins(db, f"{c.name if c else '老师'}已到店开始执案 {o.order_no}",
                 f"门店：{o.store_name or ''}，预计{duration}天", ref_id=o.id)

    db.commit()
    return {"code": 0, "msg": "执案已开始"}


# ────────── Step 5: 每日执案日志 ──────────

@admin_router.post("/orders/{order_id}/day-log")
def workflow_day_log(
    order_id: int, body: OrderDayLogIn, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status != "in_progress":
        raise HTTPException(400, "工单未在执案中")

    day_labels = {
        1: "研讨会执案中 · Day1 现状诊断",
        2: "研讨会执案中 · Day2 框架共建",
        3: "研讨会执案中 · Day3 启动会",
    }
    o.workflow_stage = day_labels.get(body.day_number, f"研讨会执案中 · Day{body.day_number}")
    o.workflow_progress = min(65, 50 + body.day_number * 5)

    _add_log(
        db, order_id, body.stage, body.content,
        images=body.images, day_number=body.day_number,
        findings=body.findings, decisions=body.decisions,
        next_actions=body.next_actions, log_type="daily",
        consultant_id=current_user.consultant_id if current_user.is_consultant else None,
    )

    db.commit()
    return {"code": 0, "msg": f"Day{body.day_number} 日志已保存"}


# ────────── Step 6: 提交执案报告（含文件上传） ──────────

@admin_router.put("/orders/{order_id}/report")
def workflow_report(
    order_id: int, body: OrderReportIn, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    """老师提交执案总报告 + 会议记录文件 + 客户方案文件"""
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status != "in_progress":
        raise HTTPException(400, "工单未在执案中")

    # ★ v2改动：直接进入跟进阶段（而非reporting等审核）
    o.status = "follow_up"
    o.workflow_stage = "执案后跟进 · 等待回访"
    o.workflow_progress = 75

    report_parts = [f"【执案总结】{body.summary}"]
    if body.problems_found:
        report_parts.append(f"【核心问题】{body.problems_found}")
    if body.solutions_built:
        report_parts.append(f"【搭建方案】{body.solutions_built}")
    if body.follow_up_plan:
        report_parts.append(f"【后续跟进计划】{body.follow_up_plan}")
    if body.next_visit_suggestion:
        report_parts.append(f"【建议下次下店】{body.next_visit_suggestion}")
    if body.meeting_records:
        report_parts.append(f"【📄 会议记录文件】{body.meeting_records}")
    if body.deliverables:
        report_parts.append(f"【📦 交付客户方案文件】{body.deliverables}")
    if body.attachments:
        report_parts.append(f"【📎 其他附件】{body.attachments}")

    _add_log(db, order_id, "执案报告", "\n".join(report_parts),
             log_type="report",
             consultant_id=current_user.consultant_id if current_user.is_consultant else None)

    # 通知管理员
    _push_admins(db, f"工单 {o.order_no} 执案报告已提交，进入跟进阶段",
                 f"总结：{body.summary[:80]}...", ref_id=o.id)

    # 通知销售老师
    member = db.query(Member).filter(Member.id == o.member_id).first()
    if member and member.consultant_id:
        sales = db.query(Consultant).filter(Consultant.id == member.consultant_id).first()
        if sales:
            _push_notif(db, "consultant", sales.id,
                f"客户 {member.name} 的专案执案报告已提交",
                f"工单号：{o.order_no}，后续需要2-3次跟进回访",
                ref_id=o.id)

    db.commit()
    return {"code": 0, "msg": "执案报告已提交，工单进入跟进阶段"}


# ────────── Step 7: 执案后跟进（2-3次回访会议） ──────────

@admin_router.post("/orders/{order_id}/followup")
def workflow_followup(
    order_id: int, body: FollowUpMeetingIn, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    """老师填写执案后跟进会议记录（共2-3次）"""
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status != "follow_up":
        raise HTTPException(400, "工单未在跟进阶段")

    # 构建日志内容
    type_label = "线上会议" if body.meeting_type == "online" else "线下会议"
    content_parts = [
        f"第{body.meeting_number}次跟进{type_label}",
        f"日期：{body.meeting_date or '未填'}",
        f"内容：{body.content}",
    ]
    if body.data_review:
        content_parts.append(f"📊 执案数据回顾：{body.data_review}")
    if body.issues:
        content_parts.append(f"⚠️ 新问题：{body.issues}")
    if body.actions:
        content_parts.append(f"📋 跟进行动项：{body.actions}")
    if body.meeting_record_file:
        content_parts.append(f"📄 会议记录文件：{body.meeting_record_file}")

    _add_log(
        db, order_id,
        f"跟进#{body.meeting_number}",
        "\n".join(content_parts),
        images=body.images,
        log_type="followup",
        day_number=body.meeting_number,
        findings=body.issues,
        decisions=body.data_review,
        next_actions=body.actions,
        consultant_id=current_user.consultant_id if current_user.is_consultant else None,
    )

    # 更新工单阶段
    o.workflow_stage = f"执案后跟进 · 第{body.meeting_number}次回访完成"
    o.workflow_progress = min(95, 75 + body.meeting_number * 5)

    # 通知管理员
    _push_admins(db, f"工单 {o.order_no} 第{body.meeting_number}次跟进已完成",
                 f"{type_label}：{body.content[:80]}", ref_id=o.id)

    db.commit()
    return {"code": 0, "msg": f"第{body.meeting_number}次跟进会议已记录"}


# ────────── Step 8: 整体执案结束（管理员审核 + 扣减套餐） ──────────

@admin_router.put("/orders/{order_id}/complete")
def workflow_complete(
    order_id: int, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    """管理员审核通过，整体执案结束，自动扣减套餐"""
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status != "follow_up":
        raise HTTPException(400, f"当前状态({o.status})不可完成，需在跟进阶段")

    o.status = "completed"
    o.workflow_stage = "整体执案结束"
    o.workflow_progress = 100

    if o.package_id:
        pkg = db.query(ServicePackage).filter(ServicePackage.id == o.package_id).first()
        if pkg and pkg.used_times < pkg.total_times:
            pkg.used_times += 1

    _add_log(db, order_id, "工单完成", "整体执案结束，套餐次数已扣减", log_type="system")

    # 通知会员评价
    member = db.query(Member).filter(Member.id == o.member_id).first()
    if member:
        from services.notify_service import send_wecom
        send_wecom(f"✅ {member.name}，您的专案服务已全部完成，请在小程序提交满意度评价。")

    db.commit()
    return {"code": 0, "msg": "整体执案结束"}


# ────────── 取消工单 ──────────

@admin_router.put("/orders/{order_id}/cancel")
def workflow_cancel(
    order_id: int, db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_consultant),
):
    o = db.query(ServiceOrder).filter(ServiceOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "工单不存在")
    if o.status in ("completed", "cancelled"):
        raise HTTPException(400, "该状态不可取消")

    o.status = "cancelled"
    o.workflow_stage = "已取消"
    o.workflow_progress = 0
    _add_log(db, order_id, "取消", "工单已取消", log_type="system")

    db.commit()
    return {"code": 0, "msg": "工单已取消"}


# ────────── 日志工具 ──────────

def _add_log(db, order_id, stage, content, images=None, log_type="note",
            consultant_id=None, day_number=None, findings=None,
            decisions=None, next_actions=None):
    log = ServiceWorkLog(
        order_id=order_id, stage=stage, content=content,
        images=images, consultant_id=consultant_id,
        day_number=day_number, findings=findings,
        decisions=decisions, next_actions=next_actions, log_type=log_type,
    )
    db.add(log)
    db.flush()
    return log
