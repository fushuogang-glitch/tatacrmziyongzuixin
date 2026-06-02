# 日历看板路由 —— 老师行程 + 客户预约实时同步
from datetime import date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, extract

from database import get_db
from models import (
    ServiceOrder, VisitBooking, Enrollment, Consultant,
    Member, Service, AdminUser
)
from models.session import Session as CourseSession
from models.booking import ConsultantSchedule
from utils.helpers import ok
from utils.auth import get_current_admin, get_admin_or_agent, get_current_admin_or_consultant


router = APIRouter(prefix="/admin/calendar", tags=["calendar"])


def _fmt_date(d) -> Optional[str]:
    return d.isoformat() if d else None


# ─────────────────────────────────────────────
# 1. 月视图：指定月份的所有事件（专案工单 + 下店预约 + 场次课程）
# ─────────────────────────────────────────────
@router.get("/month")
def month_view(
    year: int = Query(..., description="年份 2026"),
    month: int = Query(..., description="月份 1-12"),
    consultant_id: Optional[int] = Query(None, description="筛选指定老师"),
    db: Session = Depends(get_db),
    _ = Depends(get_current_admin_or_consultant),
):
    """月视图：返回该月所有日历事件列表（含专案/下店/课程）"""
    # 计算该月首日和末日
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    events = []

    # ── 专案服务工单 ──
    # 扩大查询范围：appoint_date可能在月初前但duration跨入当月
    q = db.query(ServiceOrder).filter(
        ServiceOrder.appoint_date >= first_day - timedelta(days=5),
        ServiceOrder.appoint_date <= last_day,
        ServiceOrder.status.notin_(["cancelled"]),
    )
    if consultant_id:
        q = q.filter(ServiceOrder.consultant_id == consultant_id)
    orders = q.all()

    # 批量取关联数据
    order_member_ids = [o.member_id for o in orders]
    order_service_ids = [o.service_id for o in orders if o.service_id]
    order_consultant_ids = [o.consultant_id for o in orders if o.consultant_id]

    members_map = {
        m.id: m for m in db.query(Member).filter(Member.id.in_(order_member_ids)).all()
    } if order_member_ids else {}
    services_map = {
        s.id: s for s in db.query(Service).filter(Service.id.in_(order_service_ids)).all()
    } if order_service_ids else {}
    consultants_map = {
        c.id: c for c in db.query(Consultant).filter(Consultant.id.in_(order_consultant_ids)).all()
    } if order_consultant_ids else {}

    for o in orders:
        member = members_map.get(o.member_id)
        service = services_map.get(o.service_id) if o.service_id else None
        consultant = consultants_map.get(o.consultant_id) if o.consultant_id else None
        # 按 duration_days 展开多天（默认1天）
        duration = (service.duration_days if service and service.duration_days else 1)
        base_date = o.appoint_date
        for day_offset in range(duration):
            ev_date = base_date + timedelta(days=day_offset) if base_date else None
            if ev_date and ev_date < first_day:
                continue
            if ev_date and ev_date > last_day:
                break
            day_label = f"Day{day_offset+1}/{duration}" if duration > 1 else ""
            _member_name = member.name if member else "—"
            _consultant_name = consultant.name if consultant else "待分配"
            _store = o.store_name or ""
            _day_tag = f"Day{day_offset+1}/{duration}" if duration > 1 else ""
            # 显示格式：客户·老师·门店·Day几（精简，不重复客户名）
            _chip_parts = [_member_name, _consultant_name, _store]
            if _day_tag:
                _chip_parts.append(_day_tag)
            _chip_title = " · ".join([p for p in _chip_parts if p])
            events.append({
                "id": f"order-{o.id}-d{day_offset}" if duration > 1 else f"order-{o.id}",
                "type": "service_order",
                "type_label": "专案服务",
                "date": _fmt_date(ev_date),
                "time_slot": (o.appoint_time or ""),
                "title": _chip_title,
                "member_name": _member_name,
                "member_phone": (member.phone[-4:] if member else ""),
                "consultant_name": _consultant_name,
                "consultant_id": o.consultant_id,
                "status": o.status,
                "status_label": _order_status_label(o.status),
                "color": _order_color(o.status),
                "store_name": _store,
                "order_no": o.order_no or "",
                "order_id": o.id,
                "workflow_progress": o.workflow_progress or 0,
            })

    # ── 下店预约 ──
    q2 = db.query(VisitBooking).filter(
        VisitBooking.confirmed_date >= first_day,
        VisitBooking.confirmed_date <= last_day,
        VisitBooking.status.notin_(["cancelled"]),
    )
    if consultant_id:
        q2 = q2.filter(VisitBooking.consultant_id == consultant_id)
    visits = q2.all()

    visit_member_ids = [v.member_id for v in visits if v.member_id]
    visit_consultant_ids = [v.consultant_id for v in visits if v.consultant_id]
    visit_members_map = {
        m.id: m for m in db.query(Member).filter(Member.id.in_(visit_member_ids)).all()
    } if visit_member_ids else {}
    visit_consultants_map = {
        c.id: c for c in db.query(Consultant).filter(Consultant.id.in_(visit_consultant_ids)).all()
    } if visit_consultant_ids else {}

    for v in visits:
        member = visit_members_map.get(v.member_id) if v.member_id else None
        consultant = visit_consultants_map.get(v.consultant_id) if v.consultant_id else None
        events.append({
            "id": f"visit-{v.id}",
            "type": "visit_booking",
            "type_label": "下店辅导",
            "date": _fmt_date(v.confirmed_date),
            "time_slot": f"共{v.duration_days}天",
            "title": "下店辅导",
            "member_name": member.name if member else "—",
            "member_phone": (member.phone[-4:] if member else ""),
            "consultant_name": consultant.name if consultant else "待分配",
            "consultant_id": v.consultant_id,
            "status": v.status,
            "status_label": _visit_status_label(v.status),
            "color": "#7b6fdf",
            "store_name": v.city or "",
            "order_id": v.id,
        })

    # ── 课程场次（塔塔定课，跨天展示每天一条） ──
    sessions = db.query(CourseSession).filter(
        CourseSession.start_date <= last_day,
        CourseSession.end_date >= first_day,
        CourseSession.status.notin_(["cancelled"]),
    ).all()

    for s in sessions:
        # 跨多天的课程：每天生成一条事件，方便日历格子显示
        if s.start_date and s.end_date:
            cur = max(s.start_date, first_day)
            end = min(s.end_date, last_day)
            day_count = (s.end_date - s.start_date).days + 1
            is_first = True
            while cur <= end:
                events.append({
                    "id": f"session-{s.id}-{cur.isoformat()}",
                    "type": "course_session",
                    "type_label": "课程",
                    "date": cur.isoformat(),
                    "time_slot": f"共{day_count}天",
                    "title": f"{s.session_no}" if s.session_no else "课程场次",
                    "subtitle": s.location or s.city or "",
                    "member_name": f"已报名 {s.enrolled}/{s.capacity}",
                    "member_phone": "",
                    "consultant_name": s.city or "",
                    "consultant_id": None,
                    "status": s.status,
                    "status_label": {"open": "报名中", "full": "已满员", "closed": "已截止", "finished": "已结束"}.get(s.status, s.status),
                    "color": "#e6a817",
                    "is_first_day": is_first,
                    "is_last_day": cur == end,
                    "start_date": s.start_date.isoformat(),
                    "end_date": s.end_date.isoformat(),
                    "session_id": s.id,
                    "capacity": s.capacity,
                    "enrolled": s.enrolled,
                    "store_name": s.location or "",
                    "order_id": s.id,
                })
                is_first = False
                cur += timedelta(days=1)

    # ── 老师排期（手动录入的工作安排） ──
    q_sch = db.query(ConsultantSchedule).filter(
        ConsultantSchedule.schedule_date >= first_day,
        ConsultantSchedule.schedule_date <= last_day,
    )
    if consultant_id:
        q_sch = q_sch.filter(ConsultantSchedule.consultant_id == consultant_id)
    scheds = q_sch.all()

    sch_consultant_ids = list({s.consultant_id for s in scheds if s.consultant_id})
    sch_consultants_map = {
        c.id: c for c in db.query(Consultant).filter(Consultant.id.in_(sch_consultant_ids)).all()
    } if sch_consultant_ids else {}

    _sch_type_label = {'available': '可约', 'busy': '忙碌', 'leave': '休假'}
    _sch_color = {'available': '#9b59b6', 'busy': '#e74c3c', 'leave': '#95a5a6'}

    for s in scheds:
        # 跳过已有工单关联的排期（工单已展开多天，避免重复）
        if s.order_id:
            continue
        c = sch_consultants_map.get(s.consultant_id)
        events.append({
            "id": f"schedule-{s.id}",
            "type": "consultant_schedule",
            "type_label": _sch_type_label.get(s.schedule_type, '排期'),
            "date": s.schedule_date.isoformat() if s.schedule_date else None,
            "time_slot": s.title or '',
            "title": s.title or _sch_type_label.get(s.schedule_type, '排期'),
            "member_name": s.city or '',
            "member_phone": '',
            "consultant_name": c.name if c else '',
            "consultant_id": s.consultant_id,
            "status": s.schedule_type,
            "status_label": _sch_type_label.get(s.schedule_type, '排期'),
            "color": _sch_color.get(s.schedule_type, '#9b59b6'),
            "store_name": s.city or '',
            "order_id": s.id,
        })

    # 按日期排序
    events.sort(key=lambda e: e["date"] or "")

    return ok({
        "year": year,
        "month": month,
        "total": len(events),
        "events": events,
    })


# ─────────────────────────────────────────────
# 2. 老师视图：所有老师 + 当月各自行程摘要
# ─────────────────────────────────────────────
@router.get("/consultants")
def consultants_schedule(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    _ = Depends(get_current_admin_or_consultant),
):
    """老师月度行程摘要：每位老师有多少天行程"""
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    consultants = db.query(Consultant).filter(Consultant.status == "active").all()

    result = []
    for c in consultants:
        # 该月专案工单数
        order_count = db.query(ServiceOrder).filter(
            ServiceOrder.consultant_id == c.id,
            ServiceOrder.appoint_date >= first_day,
            ServiceOrder.appoint_date <= last_day,
            ServiceOrder.status.notin_(["cancelled"]),
        ).count()

        # 该月下店预约数
        visit_count = db.query(VisitBooking).filter(
            VisitBooking.consultant_id == c.id,
            VisitBooking.confirmed_date >= first_day,
            VisitBooking.confirmed_date <= last_day,
            VisitBooking.status.notin_(["cancelled"]),
        ).count()

        # 该月忙碌天数（去重日期）
        busy_dates_orders = db.query(ServiceOrder.appoint_date).filter(
            ServiceOrder.consultant_id == c.id,
            ServiceOrder.appoint_date >= first_day,
            ServiceOrder.appoint_date <= last_day,
            ServiceOrder.status.notin_(["cancelled"]),
        ).distinct().all()

        busy_dates_visits = db.query(VisitBooking.confirmed_date).filter(
            VisitBooking.consultant_id == c.id,
            VisitBooking.confirmed_date >= first_day,
            VisitBooking.confirmed_date <= last_day,
            VisitBooking.status.notin_(["cancelled"]),
        ).distinct().all()

        busy_days = len(
            set(d[0] for d in busy_dates_orders if d[0]) |
            set(d[0] for d in busy_dates_visits if d[0])
        )

        # 老师排期（手动录入）也计入忙碌天数
        schedule_dates = db.query(ConsultantSchedule.schedule_date).filter(
            ConsultantSchedule.consultant_id == c.id,
            ConsultantSchedule.schedule_date >= first_day,
            ConsultantSchedule.schedule_date <= last_day,
        ).distinct().all()
        schedule_count = len([d[0] for d in schedule_dates if d[0]])

        all_busy = len(
            set(d[0] for d in busy_dates_orders if d[0]) |
            set(d[0] for d in busy_dates_visits if d[0]) |
            set(d[0] for d in schedule_dates if d[0])
        )

        result.append({
            "consultant_id": c.id,
            "consultant_name": c.name,
            "phone": c.phone,
            "monthly_days": c.monthly_days,
            "course_days": c.course_days,
            "busy_days": all_busy,
            "free_days": max(0, (c.monthly_days or 14) - all_busy),
            "order_count": order_count,
            "visit_count": visit_count,
            "schedule_count": schedule_count,
        })

    return ok(result)


# ─────────────────────────────────────────────
# 3. 日视图：指定日期所有事件（含时间轴排列）
# ─────────────────────────────────────────────
@router.get("/day")
def day_view(
    day: str = Query(..., description="日期 YYYY-MM-DD"),
    consultant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _ = Depends(get_current_admin_or_consultant),
):
    """日视图：指定日期的详细时间轴事件"""
    target = date.fromisoformat(day)

    events = []

    # 专案工单
    q = db.query(ServiceOrder).filter(
        ServiceOrder.appoint_date == target,
        ServiceOrder.status.notin_(["cancelled"]),
    )
    if consultant_id:
        q = q.filter(ServiceOrder.consultant_id == consultant_id)
    orders = q.all()

    member_ids = [o.member_id for o in orders]
    service_ids = [o.service_id for o in orders if o.service_id]
    consultant_ids = [o.consultant_id for o in orders if o.consultant_id]

    members_map = {m.id: m for m in db.query(Member).filter(Member.id.in_(member_ids)).all()} if member_ids else {}
    services_map = {s.id: s for s in db.query(Service).filter(Service.id.in_(service_ids)).all()} if service_ids else {}
    consultants_map = {c.id: c for c in db.query(Consultant).filter(Consultant.id.in_(consultant_ids)).all()} if consultant_ids else {}

    for o in orders:
        member = members_map.get(o.member_id)
        service = services_map.get(o.service_id) if o.service_id else None
        consultant = consultants_map.get(o.consultant_id) if o.consultant_id else None
        events.append({
            "id": f"order-{o.id}",
            "type": "service_order",
            "type_label": "专案服务",
            "time_slot": o.appoint_time or "全天",
            "title": service.name if service else "专案服务",
            "member_name": member.name if member else "—",
            "member_phone": member.phone if member else "",
            "member_enterprise": member.enterprise_name if member else "",
            "consultant_name": consultant.name if consultant else "待分配",
            "consultant_phone": consultant.phone if consultant else "",
            "status": o.status,
            "status_label": _order_status_label(o.status),
            "color": _order_color(o.status),
            "store_name": o.store_name or "",
            "store_address": o.store_address or "",
            "workflow_stage": o.workflow_stage or "",
            "workflow_progress": o.workflow_progress or 0,
            "order_no": o.order_no or "",
            "order_id": o.id,
        })

    # 下店预约
    q2 = db.query(VisitBooking).filter(
        VisitBooking.confirmed_date == target,
        VisitBooking.status.notin_(["cancelled"]),
    )
    if consultant_id:
        q2 = q2.filter(VisitBooking.consultant_id == consultant_id)
    visits = q2.all()

    for v in visits:
        member = members_map.get(v.member_id) if v.member_id else None
        consultant = visit_consultants_map_d = (
            db.query(Consultant).filter(Consultant.id == v.consultant_id).first()
            if v.consultant_id else None
        )
        events.append({
            "id": f"visit-{v.id}",
            "type": "visit_booking",
            "type_label": "下店辅导",
            "time_slot": f"共{v.duration_days}天",
            "title": "下店辅导",
            "member_name": member.name if member else "—",
            "member_phone": member.phone if member else "",
            "consultant_name": consultant.name if consultant else "待分配",
            "status": v.status,
            "status_label": _visit_status_label(v.status),
            "color": "#7b6fdf",
            "store_name": v.city or "",
        })

    # 课程场次（塔塔定课，当天有课程就显示）
    sessions_day = db.query(CourseSession).filter(
        CourseSession.start_date <= target,
        CourseSession.end_date >= target,
        CourseSession.status.notin_(["cancelled"]),
    ).all()
    for s in sessions_day:
        day_count = (s.end_date - s.start_date).days + 1 if s.end_date and s.start_date else 1
        events.append({
            "id": f"session-{s.id}",
            "type": "course_session",
            "type_label": "课程",
            "time_slot": f"共{day_count}天 ({s.start_date}~{s.end_date})",
            "title": s.session_no or "课程场次",
            "member_name": f"已报名 {s.enrolled}/{s.capacity} 人",
            "member_phone": "",
            "consultant_name": s.city or "",
            "status": s.status,
            "status_label": {"open": "报名中", "full": "已满员", "closed": "已截止", "finished": "已结束"}.get(s.status, s.status),
            "color": "#e6a817",
            "store_name": s.location or "",
            "session_id": s.id,
        })

    return ok({
        "date": day,
        "total": len(events),
        "events": events,
    })


# ─────────────────────────────────────────────
# 4. 空闲时段查询（小程序预约时用）
# ─────────────────────────────────────────────
@router.get("/available-slots")
def available_slots(
    consultant_id: int = Query(...),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """查询老师在日期范围内的可用时段（无需登录，供小程序调用）"""
    return _calc_slots(consultant_id, start_date, end_date, db)


# ── 小程序公开接口（无需token） ──
public_router = APIRouter(prefix="/api/calendar", tags=["public-calendar"])


@public_router.get("/consultants")
def public_consultants(service_id: Optional[int] = None, db: Session = Depends(get_db)):
    """小程序选老师：返回活跃老师，可按service_id过滤"""
    consultants = db.query(Consultant).filter(Consultant.status == "active").all()
    result = []
    # 如果指定了service_id，按service_modules过滤
    service_name = None
    if service_id:
        svc = db.query(Service).filter(Service.id == service_id).first()
        if svc:
            service_name = svc.name
    for c in consultants:
        if service_name and c.service_modules:
            import json as _json
            try:
                modules = _json.loads(c.service_modules)
                if service_name not in modules:
                    continue
            except Exception:
                pass
        result.append({
            "id": c.id,
            "name": c.name,
            "specialty": c.specialty or "",
            "service_modules": c.service_modules or "[]",
            "avatar": c.avatar or "",
        })
    return ok(result)


@public_router.get("/slots")
def public_slots(
    consultant_id: int = Query(...),
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """小程序查排期：日期+状态（available/busy/leave）+颜色"""
    return _calc_slots(consultant_id, start_date, end_date, db)


def _calc_slots(consultant_id: int, start_date: str, end_date: str, db: Session):
    """核心排期计算：合并工单+下店预约+手动排期"""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    # 专案工单占用
    busy_orders = db.query(ServiceOrder.appoint_date).filter(
        ServiceOrder.consultant_id == consultant_id,
        ServiceOrder.appoint_date >= start,
        ServiceOrder.appoint_date <= end,
        ServiceOrder.status.notin_(["cancelled"]),
    ).all()
    order_dates = set(d[0].isoformat() for d in busy_orders if d[0])

    # 下店预约占用
    busy_visits = db.query(VisitBooking.confirmed_date).filter(
        VisitBooking.consultant_id == consultant_id,
        VisitBooking.confirmed_date >= start,
        VisitBooking.confirmed_date <= end,
        VisitBooking.status.notin_(["cancelled"]),
    ).all()
    visit_dates = set(d[0].isoformat() for d in busy_visits if d[0])

    # 手动排期（含 busy / leave / available）
    schedules = db.query(ConsultantSchedule).filter(
        ConsultantSchedule.consultant_id == consultant_id,
        ConsultantSchedule.schedule_date >= start,
        ConsultantSchedule.schedule_date <= end,
    ).all()
    # date → schedule_type + title
    sch_map = {}
    for s in schedules:
        if s.schedule_date:
            key = s.schedule_date.isoformat()
            sch_map[key] = {
                "type": s.schedule_type or "busy",
                "title": s.title or "",
                "city": s.city or "",
            }

    all_busy = order_dates | visit_dates

    # 颜色映射
    color_map = {"busy": "#e74c3c", "leave": "#95a5a6", "available": "#52c41a"}
    label_map = {"busy": "忙碌", "leave": "休假", "available": "可约"}

    slots = []
    cur = start
    while cur <= end:
        ds = cur.isoformat()
        sch = sch_map.get(ds)

        if ds in all_busy:
            status = "busy"
            title = sch["title"] if sch else "已占用"
        elif sch:
            status = sch["type"]
            title = sch["title"]
        else:
            status = "available"
            title = ""

        slots.append({
            "date": ds,
            "status": status,
            "status_label": label_map.get(status, "可约"),
            "color": color_map.get(status, "#52c41a"),
            "available": status == "available",
            "title": title,
            "weekday": cur.strftime("%A"),
        })
        cur += timedelta(days=1)

    return ok({
        "consultant_id": consultant_id,
        "slots": slots,
        "busy_count": len([s for s in slots if not s["available"]]),
    })


# ─────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────
def _order_status_label(status: str) -> str:
    return {
        "pending": "待确认",
        "confirmed": "已确认",
        "in_progress": "执行中",
        "completed": "已完成",
        "cancelled": "已取消",
    }.get(status, status)


def _visit_status_label(status: str) -> str:
    return {
        "pending": "待确认",
        "confirmed": "已确认",
        "completed": "已完成",
        "cancelled": "已取消",
    }.get(status, status)


def _order_color(status: str) -> str:
    return {
        "pending": "#e6a817",
        "confirmed": "#c9a96e",
        "in_progress": "#4a90d9",
        "completed": "#52c41a",
        "cancelled": "#999",
    }.get(status, "#c9a96e")
