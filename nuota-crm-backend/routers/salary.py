"""薪资管理路由"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import get_db
from models import AdminUser
from models.booking import Consultant
from utils.auth import get_current_admin, get_admin_or_agent
from utils.helpers import ok

router = APIRouter(prefix="/admin/salary", tags=["salary"])


# ────────── 薪资配置 ──────────

@router.get("/configs")
def list_salary_configs(db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    """获取所有级别薪资配置"""
    rows = db.execute(text(
        "SELECT * FROM salary_configs ORDER BY sort_order"
    )).mappings().all()
    return ok([dict(r) for r in rows])


@router.put("/configs/{level}")
def update_salary_config(level: str, body: dict, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    """更新某级别薪资配置"""
    fields = ['base_salary', 'social_subsidy', 'travel_allowance', 'daily_allowance',
              'commission_rate', 'branch_mgmt', 'dept_mgmt', 'course_invite',
              'assist_travel_allowance', 'assist_daily_allowance']
    sets = []
    params = {"level": level}
    for f in fields:
        if f in body:
            sets.append(f"{f} = :{f}")
            params[f] = body[f]
    if not sets:
        raise HTTPException(400, "无更新字段")
    sql = f"UPDATE salary_configs SET {', '.join(sets)} WHERE level = :level"
    db.execute(text(sql), params)
    db.commit()
    return ok({"msg": "已更新"})


# ────────── 岗位津贴 ──────────

@router.get("/positions")
def list_positions(db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    rows = db.execute(text("SELECT * FROM position_allowances ORDER BY id")).mappings().all()
    return ok([dict(r) for r in rows])


@router.put("/positions/{pos_id}")
def update_position(pos_id: int, body: dict, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    db.execute(text("UPDATE position_allowances SET monthly_amount = :amt WHERE id = :id"),
               {"amt": body.get("monthly_amount", 0), "id": pos_id})
    db.commit()
    return ok({"msg": "已更新"})


# ────────── 月度算薪 ──────────

@router.post("/calculate")
def calculate_salary(
    body: dict,
    db: Session = Depends(get_db),
    admin=Depends(get_admin_or_agent)
):
    """计算指定月份所有老师工资"""
    year = body.get("year", date.today().year)
    month = body.get("month", date.today().month)
    consultant_id = body.get("consultant_id")  # 可选，指定单个老师

    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1)
    else:
        last_day = date(year, month + 1, 1)

    # 加载薪资配置
    configs = {}
    for r in db.execute(text("SELECT * FROM salary_configs")).mappings().all():
        configs[r["level"]] = dict(r)

    # 加载岗位津贴
    pos_allowances = {}
    for r in db.execute(text("SELECT * FROM position_allowances")).mappings().all():
        pos_allowances[r["position"]] = dict(r)

    # 查老师
    q = db.query(Consultant).filter(Consultant.status == "active")
    if consultant_id:
        q = q.filter(Consultant.id == consultant_id)
    teachers = q.all()

    from models.service import ServiceOrder
    from models.member import Member, Payment

    results = []
    for t in teachers:
        cfg = configs.get(t.level, configs.get("trainee", {}))

        # 主案出差天数
        try:
            main_days = db.query(func.count(func.distinct(ServiceOrder.appoint_date))).filter(
                ServiceOrder.consultant_id == t.id,
                ServiceOrder.appoint_date >= first_day,
                ServiceOrder.appoint_date < last_day,
                ServiceOrder.status.notin_(["cancelled", "rejected"]),
            ).scalar() or 0
        except:
            main_days = 0

        # 助理出差天数
        try:
            assist_days = db.query(func.count(func.distinct(ServiceOrder.appoint_date))).filter(
                ServiceOrder.assistant_id == t.id,
                ServiceOrder.appoint_date >= first_day,
                ServiceOrder.appoint_date < last_day,
                ServiceOrder.status.notin_(["cancelled", "rejected"]),
            ).scalar() or 0
        except:
            assist_days = 0

        # 回款金额（按客户归属计算，归属谁业绩就是谁的）
        try:
            collection = float(db.execute(text("""
                SELECT COALESCE(SUM(p.amount), 0)
                FROM payments p
                JOIN members m ON m.id = p.member_id
                WHERE m.consultant_id = :cid
                AND p.pay_status = 'completed'
                AND p.created_at >= :fd AND p.created_at < :ld
            """), {"cid": t.id, "fd": first_day, "ld": last_day}).scalar() or 0)
        except:
            collection = 0.0

        # 计算各项
        base = float(cfg.get("base_salary", 3000))
        social = float(cfg.get("social_subsidy", 2000))
        travel = float(cfg.get("travel_allowance", 0)) if main_days > 0 else 0
        daily_total = float(cfg.get("daily_allowance", 0)) * main_days
        commission_rate = float(cfg.get("commission_rate", 0))
        commission_amount = collection * commission_rate

        # 助理津贴
        assist_travel = float(cfg.get("assist_travel_allowance", 500)) if assist_days > 0 else 0
        assist_daily_total = 300 * assist_days  # 助理统一300/天

        # 岗位津贴
        position_allow = 0
        if t.position and t.position in pos_allowances:
            pa = pos_allowances[t.position]
            position_allow = float(pa.get("monthly_amount", 0))

        # 管理津贴（按配置）
        branch_mgmt = float(cfg.get("branch_mgmt", 0)) if t.position and "分公司" in (t.position or "") else 0
        dept_mgmt = float(cfg.get("dept_mgmt", 0)) if t.position else 0

        total = base + social + travel + daily_total + commission_amount + assist_travel + assist_daily_total + position_allow + branch_mgmt + dept_mgmt

        # 写入记录
        db.execute(text("""
            INSERT INTO salary_records
            (consultant_id, year, month, level, base_salary, social_subsidy,
             travel_allowance, daily_allowance_total, main_days, assist_days,
             assist_allowance_total, commission_amount, commission_base, commission_rate,
             position_allowance, course_invite_amount, total_salary, status, updated_at)
            VALUES (:cid, :year, :month, :level, :base, :social,
                    :travel, :daily_total, :main_days, :assist_days,
                    :assist_total, :commission, :comm_base, :comm_rate,
                    :pos_allow, 0, :total, 'draft', NOW())
            ON CONFLICT (consultant_id, year, month) DO UPDATE SET
                level = :level, base_salary = :base, social_subsidy = :social,
                travel_allowance = :travel, daily_allowance_total = :daily_total,
                main_days = :main_days, assist_days = :assist_days,
                assist_allowance_total = :assist_total,
                commission_amount = :commission, commission_base = :comm_base,
                commission_rate = :comm_rate, position_allowance = :pos_allow,
                total_salary = :total, status = 'draft', updated_at = NOW()
        """), {
            "cid": t.id, "year": year, "month": month, "level": t.level or "trainee",
            "base": base, "social": social, "travel": travel,
            "daily_total": daily_total, "main_days": main_days,
            "assist_days": assist_days, "assist_total": assist_travel + assist_daily_total,
            "commission": commission_amount, "comm_base": collection, "comm_rate": commission_rate,
            "pos_allow": position_allow + branch_mgmt + dept_mgmt, "total": total,
        })

        results.append({
            "consultant_id": t.id,
            "name": t.name,
            "level": t.level,
            "base_salary": base,
            "social_subsidy": social,
            "travel_allowance": travel,
            "daily_allowance_total": daily_total,
            "main_days": main_days,
            "assist_days": assist_days,
            "assist_allowance_total": assist_travel + assist_daily_total,
            "commission_base": collection,
            "commission_rate": commission_rate,
            "commission_amount": commission_amount,
            "position_allowance": position_allow + branch_mgmt + dept_mgmt,
            "total_salary": total,
        })

    db.commit()
    return ok({"year": year, "month": month, "records": results})


# ────────── 工资记录查询 ──────────

@router.get("/records")
def list_salary_records(
    year: int = None, month: int = None,
    db: Session = Depends(get_db), _=Depends(get_admin_or_agent)
):
    """查询月度工资记录"""
    if not year:
        year = date.today().year
    if not month:
        month = date.today().month

    rows = db.execute(text("""
        SELECT sr.*, c.name as consultant_name, c.phone, c.position
        FROM salary_records sr
        JOIN consultants c ON c.id = sr.consultant_id
        WHERE sr.year = :year AND sr.month = :month
        ORDER BY sr.total_salary DESC
    """), {"year": year, "month": month}).mappings().all()
    return ok([dict(r) for r in rows])


@router.post("/records/{record_id}/confirm")
def confirm_salary(record_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_or_agent)):
    """确认工资"""
    db.execute(text(
        "UPDATE salary_records SET status = 'confirmed', confirmed_by = :admin_id, confirmed_at = NOW() WHERE id = :id"
    ), {"id": record_id, "admin_id": admin.id})
    db.commit()
    return ok({"msg": "已确认"})


@router.post("/records/confirm-all")
def confirm_all_salary(body: dict, db: Session = Depends(get_db), admin=Depends(get_admin_or_agent)):
    """批量确认"""
    year = body.get("year", date.today().year)
    month = body.get("month", date.today().month)
    db.execute(text(
        "UPDATE salary_records SET status = 'confirmed', confirmed_by = :admin_id, confirmed_at = NOW() WHERE year = :year AND month = :month AND status = 'draft'"
    ), {"year": year, "month": month, "admin_id": admin.id})
    db.commit()
    return ok({"msg": "全部确认"})
