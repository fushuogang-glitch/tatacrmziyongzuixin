"""晋级管理路由"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from database import get_db
from models.booking import Consultant
from utils.auth import get_current_admin, get_admin_or_agent
from utils.helpers import ok

router = APIRouter(prefix="/admin/promotion", tags=["promotion"])

PARTNER_LEVELS = ('junior_partner', 'partner', 'senior_partner', 'founding_partner')

LEVEL_ORDER = {
    'probation': 1, 'trainee': 2, 'pm': 3, 'pd': 4,
    'junior_partner': 5, 'partner': 6, 'senior_partner': 7, 'founding_partner': 8
}


def _eval_mentee_reqs_list(mentees, reqs_list):
    """评估一组AND条件，返回 (met, details)"""
    details = []
    all_met = True
    for req in reqs_list:
        req_level = req["level"]
        req_min = req["min"]
        req_label = req.get("label", req_level)
        req_order = LEVEL_ORDER.get(req_level, 0)
        actual = sum(1 for m in mentees if LEVEL_ORDER.get(m.level, 0) >= req_order)
        met = actual >= req_min
        if not met:
            all_met = False
        details.append({
            "label": req_label, "level": req_level,
            "min": req_min, "actual": actual, "met": met,
        })
    return all_met, details


def _check_mentee_level_reqs(db: Session, mentor_id: int, level_reqs) -> dict:
    """检查带队人员是否满足分级别要求
    支持两种格式:
    1. 列表(AND): [{"level": "pm", "min": 1, "label": "项目经理"}, ...]
    2. OR模式: {"mode": "or", "options": [[req1, req2], [req3, req4]]}
    返回: {"met": bool, "details": [...], "mode": "and"|"or", "matched_option": int|null}
    """
    if not level_reqs:
        return {"met": True, "details": [], "mode": "and", "matched_option": None}

    mentees = db.query(Consultant).filter(
        Consultant.mentor_id == mentor_id,
        Consultant.status == "active",
    ).all()

    # OR模式
    if isinstance(level_reqs, dict) and level_reqs.get("mode") == "or":
        options = level_reqs.get("options", [])
        best_option = None
        best_details = []
        any_met = False
        all_options_details = []
        for i, opt in enumerate(options):
            met, details = _eval_mentee_reqs_list(mentees, opt)
            all_options_details.append({"option_index": i, "met": met, "details": details})
            if met and not any_met:
                any_met = True
                best_option = i
                best_details = details
        # 如果没有一个满足，取第一个option的details展示
        if not any_met and all_options_details:
            best_details = all_options_details[0]["details"]
        return {
            "met": any_met,
            "details": best_details,
            "mode": "or",
            "matched_option": best_option,
            "all_options": all_options_details,
        }

    # AND模式（列表）
    all_met, details = _eval_mentee_reqs_list(mentees, level_reqs)
    return {"met": all_met, "details": details, "mode": "and", "matched_option": None}


# ────────── 晋级规则 ──────────

@router.get("/rules")
def list_rules(db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    rows = db.execute(text("SELECT * FROM promotion_rules ORDER BY sort_order")).mappings().all()
    return ok([dict(r) for r in rows])


@router.put("/rules/{level}")
def update_rule(level: str, body: dict, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    fields = ['sales_target', 'min_work_days', 'min_mentees', 'mentee_desc',
              'core_requirement', 'need_partner_vote', 'vote_pass_rate', 'mentee_level_reqs']
    sets, params = [], {"level": level}
    for f in fields:
        if f in body:
            if f == 'mentee_level_reqs':
                import json
                sets.append(f"{f} = :mlr")
                params["mlr"] = json.dumps(body[f]) if body[f] else None
            else:
                sets.append(f"{f} = :{f}")
                params[f] = body[f]
    if not sets:
        raise HTTPException(400, "无更新字段")
    db.execute(text(f"UPDATE promotion_rules SET {', '.join(sets)} WHERE level = :level"), params)
    db.commit()
    return ok({"msg": "已更新"})


# ────────── 手动修正值（override）CRUD ──────────

@router.get("/overrides")
def list_overrides(year: int = None, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    if not year:
        year = date.today().year
    rows = db.execute(text(
        "SELECT po.*, c.name FROM promotion_overrides po JOIN consultants c ON c.id = po.consultant_id WHERE po.year = :y"
    ), {"y": year}).mappings().all()
    return ok([dict(r) for r in rows])


@router.put("/overrides/{consultant_id}")
def upsert_override(consultant_id: int, body: dict, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    year = body.get("year", date.today().year)
    sales = body.get("sales_override")
    days = body.get("work_days_override")
    mentees = body.get("mentees_override")
    remark = body.get("remark", "")

    db.execute(text("""
        INSERT INTO promotion_overrides (consultant_id, year, sales_override, work_days_override, mentees_override, remark, updated_at)
        VALUES (:cid, :y, :sales, :days, :mentees, :remark, NOW())
        ON CONFLICT (consultant_id, year) DO UPDATE SET
            sales_override = COALESCE(:sales, promotion_overrides.sales_override),
            work_days_override = COALESCE(:days, promotion_overrides.work_days_override),
            mentees_override = COALESCE(:mentees, promotion_overrides.mentees_override),
            remark = CASE WHEN :remark = '' THEN promotion_overrides.remark ELSE :remark END,
            updated_at = NOW()
    """), {"cid": consultant_id, "y": year, "sales": sales, "days": days, "mentees": mentees, "remark": remark})
    db.commit()
    return ok({"msg": "修正值已保存"})


@router.delete("/overrides/{consultant_id}")
def delete_override(consultant_id: int, year: int = None, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    if not year:
        year = date.today().year
    db.execute(text("DELETE FROM promotion_overrides WHERE consultant_id = :cid AND year = :y"),
               {"cid": consultant_id, "y": year})
    db.commit()
    return ok({"msg": "已删除修正值，恢复自动计算"})


# ────────── 晋级进度（每位老师当前达标情况）──────────

@router.get("/progress")
def get_progress(year: int = None, branch_id: int = None, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    if not year:
        year = date.today().year
    first_day = date(year, 1, 1)
    last_day = date(year + 1, 1, 1)

    # 加载规则
    rules = {}
    for r in db.execute(text("SELECT * FROM promotion_rules ORDER BY sort_order")).mappings().all():
        rules[r["level"]] = dict(r)

    # 加载手动修正值
    overrides = {}
    for r in db.execute(text("SELECT * FROM promotion_overrides WHERE year = :y"), {"y": year}).mappings().all():
        overrides[r["consultant_id"]] = dict(r)

    teachers = db.query(Consultant).filter(Consultant.status == "active").all()

    from models.service import ServiceOrder
    from models.member import Payment

    results = []
    for t in teachers:
        current_rule = rules.get(t.level, {})
        current_sort = current_rule.get("sort_order", 0)
        ov = overrides.get(t.id, {})

        # 找下一级
        next_rule = None
        for lv, rule in sorted(rules.items(), key=lambda x: x[1]["sort_order"]):
            if rule["sort_order"] == current_sort + 1:
                next_rule = rule
                break

        if not next_rule:
            results.append({
                "consultant_id": t.id, "name": t.name, "level": t.level, "branch_id": t.branch_id,
                "level_name": current_rule.get("level_name", t.level),
                "next_level": None, "next_level_name": "已达最高级",
                "progress": None, "year": year,
                "has_override": bool(ov),
            })
            continue

        # 年度累计销售（按客户归属计算，归属谁业绩就是谁的）
        try:
            auto_sales = float(db.execute(text("""
                SELECT COALESCE(SUM(p.amount), 0)
                FROM payments p
                JOIN members m ON m.id = p.member_id
                WHERE m.consultant_id = :cid
                AND p.pay_status = 'completed'
                AND p.created_at >= :fd AND p.created_at < :ld
            """), {"cid": t.id, "fd": first_day, "ld": last_day}).scalar() or 0)
        except:
            auto_sales = 0

        # 年度累计执案天数（工单合计 = 主案天数 + 助理天数，与工资算法一致）
        try:
            main_days = db.query(func.count(ServiceOrder.id)).filter(
                ServiceOrder.consultant_id == t.id,
                ServiceOrder.appoint_date >= first_day,
                ServiceOrder.appoint_date < last_day,
                ServiceOrder.status.notin_(["cancelled", "rejected"]),
            ).scalar() or 0
            assist_days = db.query(func.count(ServiceOrder.id)).filter(
                ServiceOrder.assistant_id == t.id,
                ServiceOrder.appoint_date >= first_day,
                ServiceOrder.appoint_date < last_day,
                ServiceOrder.status.notin_(["cancelled", "rejected"]),
            ).scalar() or 0
            auto_work_days = main_days + assist_days
        except:
            auto_work_days = 0

        # 带队：检查分级别要求
        mentee_level_reqs = next_rule.get("mentee_level_reqs")
        if mentee_level_reqs:
            mentee_check = _check_mentee_level_reqs(db, t.id, mentee_level_reqs)
        else:
            # 无分级别要求，退回总数检查
            auto_mentees = db.query(func.count(Consultant.id)).filter(
                Consultant.mentor_id == t.id,
                Consultant.status == "active",
            ).scalar() or 0
            target_mentees = next_rule.get("min_mentees", 0)
            mentee_check = {
                "met": target_mentees == 0 or auto_mentees >= target_mentees,
                "details": [{"label": "总带队人数", "level": "any", "min": target_mentees, "actual": auto_mentees, "met": target_mentees == 0 or auto_mentees >= target_mentees}],
                "mode": "and", "matched_option": None,
            }

        # 合并修正值
        sales = float(ov["sales_override"]) if ov.get("sales_override") is not None else auto_sales
        work_days = int(ov["work_days_override"]) if ov.get("work_days_override") is not None else auto_work_days

        target_sales = float(next_rule.get("sales_target", 0))
        target_days = next_rule.get("min_work_days", 0)

        progress = {
            "sales": {
                "actual": sales, "auto": auto_sales,
                "override": float(ov["sales_override"]) if ov.get("sales_override") is not None else None,
                "target": target_sales, "met": target_sales == 0 or sales >= target_sales,
            },
            "work_days": {
                "actual": work_days, "auto": auto_work_days,
                "override": int(ov["work_days_override"]) if ov.get("work_days_override") is not None else None,
                "target": target_days, "met": target_days == 0 or work_days >= target_days,
            },
            "mentees": {
                "met": mentee_check["met"],
                "details": mentee_check["details"],
                "has_level_reqs": bool(mentee_level_reqs),
                "mode": mentee_check.get("mode", "and"),
                "matched_option": mentee_check.get("matched_option"),
                "all_options": mentee_check.get("all_options"),
            },
        }
        all_met = progress["sales"]["met"] and progress["work_days"]["met"] and progress["mentees"]["met"]

        # 检查是否已有申请
        existing = db.execute(text(
            "SELECT id, status FROM promotion_applications WHERE consultant_id = :cid AND target_level = :tl AND year = :y"
        ), {"cid": t.id, "tl": next_rule["level"], "y": year}).mappings().first()

        results.append({
            "consultant_id": t.id, "name": t.name, "level": t.level, "branch_id": t.branch_id,
            "level_name": current_rule.get("level_name", t.level),
            "next_level": next_rule["level"], "next_level_name": next_rule["level_name"],
            "progress": progress, "all_met": all_met, "year": year,
            "need_partner_vote": next_rule.get("need_partner_vote", False),
            "application": dict(existing) if existing else None,
            "has_override": bool(ov),
            "override_remark": ov.get("remark", ""),
        })

    # 按级别排序（高→低）
    results.sort(key=lambda r: LEVEL_ORDER.get(r['level'], 0), reverse=True)
    return ok(results)


# ────────── 发起晋级申请 ──────────

@router.post("/apply")
def apply_promotion(body: dict, db: Session = Depends(get_db), admin=Depends(get_admin_or_agent)):
    cid = body["consultant_id"]
    target_level = body["target_level"]
    year = body.get("year", date.today().year)

    t = db.query(Consultant).filter(Consultant.id == cid).first()
    if not t:
        raise HTTPException(404, "老师不存在")

    dup = db.execute(text(
        "SELECT id FROM promotion_applications WHERE consultant_id = :cid AND target_level = :tl AND year = :y AND status IN ('pending','voting')"
    ), {"cid": cid, "tl": target_level, "y": year}).first()
    if dup:
        raise HTTPException(400, "该老师本年度已有进行中的晋级申请")

    first_day = date(year, 1, 1)
    last_day = date(year + 1, 1, 1)
    from models.service import ServiceOrder
    from models.member import Payment

    try:
        sales = float(db.execute(text("""
            SELECT COALESCE(SUM(p.amount), 0)
            FROM payments p
            JOIN members m ON m.id = p.member_id
            WHERE m.consultant_id = :cid
            AND p.pay_status = 'completed'
            AND p.created_at >= :fd AND p.created_at < :ld
        """), {"cid": cid, "fd": first_day, "ld": last_day}).scalar() or 0)
    except:
        sales = 0
    try:
        main_d = db.query(func.count(ServiceOrder.id)).filter(
            ServiceOrder.consultant_id == cid,
            ServiceOrder.appoint_date >= first_day, ServiceOrder.appoint_date < last_day,
            ServiceOrder.status.notin_(["cancelled", "rejected"]),
        ).scalar() or 0
        assist_d = db.query(func.count(ServiceOrder.id)).filter(
            ServiceOrder.assistant_id == cid,
            ServiceOrder.appoint_date >= first_day, ServiceOrder.appoint_date < last_day,
            ServiceOrder.status.notin_(["cancelled", "rejected"]),
        ).scalar() or 0
        work_days = main_d + assist_d
    except:
        work_days = 0
    mentees = db.query(func.count(Consultant.id)).filter(
        Consultant.mentor_id == cid, Consultant.status == "active"
    ).scalar() or 0

    rule = db.execute(text("SELECT * FROM promotion_rules WHERE level = :l"), {"l": target_level}).mappings().first()
    need_vote = rule and rule.get("need_partner_vote", False)
    status = "voting" if need_vote else "pending"

    db.execute(text("""
        INSERT INTO promotion_applications (consultant_id, current_level, target_level, year,
            sales_actual, work_days_actual, mentees_actual, status, remark)
        VALUES (:cid, :cl, :tl, :y, :sales, :days, :mentees, :status, :remark)
        ON CONFLICT (consultant_id, target_level, year) DO UPDATE SET
            sales_actual = :sales, work_days_actual = :days, mentees_actual = :mentees,
            status = :status, applied_at = NOW()
    """), {
        "cid": cid, "cl": t.level, "tl": target_level, "y": year,
        "sales": sales, "days": work_days, "mentees": mentees,
        "status": status, "remark": body.get("remark", ""),
    })
    db.commit()
    return ok({"msg": "晋级申请已提交" + ("，等待合伙人投票" if need_vote else ""), "status": status})


# ────────── 晋级申请列表 ──────────

@router.get("/applications")
def list_applications(year: int = None, status: str = None,
                      db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    if not year:
        year = date.today().year
    sql = """
        SELECT pa.*, c.name as consultant_name, c.phone,
            (SELECT COUNT(*) FROM promotion_votes pv WHERE pv.application_id = pa.id) as vote_count,
            (SELECT COUNT(*) FROM promotion_votes pv WHERE pv.application_id = pa.id AND pv.vote = 'approve') as approve_count
        FROM promotion_applications pa
        JOIN consultants c ON c.id = pa.consultant_id
        WHERE pa.year = :year
    """
    params = {"year": year}
    if status:
        sql += " AND pa.status = :status"
        params["status"] = status
    sql += " ORDER BY pa.applied_at DESC"
    rows = db.execute(text(sql), params).mappings().all()
    return ok([dict(r) for r in rows])


# ────────── 合伙人投票 ──────────

@router.get("/applications/{app_id}/votes")
def get_votes(app_id: int, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    rows = db.execute(text("""
        SELECT pv.*, c.name as voter_name FROM promotion_votes pv
        JOIN consultants c ON c.id = pv.voter_id
        WHERE pv.application_id = :aid ORDER BY pv.voted_at
    """), {"aid": app_id}).mappings().all()

    total_partners = db.query(func.count(Consultant.id)).filter(
        Consultant.status == "active",
        Consultant.level.in_(PARTNER_LEVELS),
    ).scalar() or 0

    app = db.execute(text("SELECT consultant_id FROM promotion_applications WHERE id = :id"), {"id": app_id}).mappings().first()
    if app:
        total_partners = max(total_partners - 1, 1)

    return ok({
        "votes": [dict(r) for r in rows],
        "total_partners": total_partners,
        "voted_count": len(rows),
        "approve_count": sum(1 for r in rows if r["vote"] == "approve"),
    })


@router.post("/applications/{app_id}/vote")
def cast_vote(app_id: int, body: dict, db: Session = Depends(get_db), admin=Depends(get_admin_or_agent)):
    vote = body.get("vote")
    comment = body.get("comment", "")
    voter_id = body.get("voter_id")

    if vote not in ("approve", "reject"):
        raise HTTPException(400, "vote必须是approve或reject")
    if not voter_id:
        raise HTTPException(400, "需指定投票人voter_id")

    app = db.execute(text("SELECT * FROM promotion_applications WHERE id = :id"), {"id": app_id}).mappings().first()
    if not app:
        raise HTTPException(404, "申请不存在")
    if app["status"] not in ("voting", "pending"):
        raise HTTPException(400, "申请状态不可投票")

    if voter_id == app["consultant_id"]:
        raise HTTPException(400, "不能给自己的晋级申请投票")

    voter = db.query(Consultant).filter(Consultant.id == voter_id).first()
    if not voter or voter.level not in PARTNER_LEVELS:
        raise HTTPException(400, "投票人必须是初级合伙人及以上")

    db.execute(text("""
        INSERT INTO promotion_votes (application_id, voter_id, vote, comment)
        VALUES (:aid, :vid, :vote, :comment)
        ON CONFLICT (application_id, voter_id) DO UPDATE SET
            vote = :vote, comment = :comment, voted_at = NOW()
    """), {"aid": app_id, "vid": voter_id, "vote": vote, "comment": comment})
    db.commit()

    _check_vote_result(app_id, db)
    return ok({"msg": "投票成功"})


def _check_vote_result(app_id: int, db: Session):
    app = db.execute(text("SELECT * FROM promotion_applications WHERE id = :id"), {"id": app_id}).mappings().first()
    if not app or app["status"] not in ("voting", "pending"):
        return

    rule = db.execute(text("SELECT * FROM promotion_rules WHERE level = :l"),
                      {"l": app["target_level"]}).mappings().first()
    pass_rate = float(rule["vote_pass_rate"]) if rule else 0.80

    total = db.query(func.count(Consultant.id)).filter(
        Consultant.status == "active",
        Consultant.level.in_(PARTNER_LEVELS),
        Consultant.id != app["consultant_id"],
    ).scalar() or 1

    votes = db.execute(text(
        "SELECT vote FROM promotion_votes WHERE application_id = :aid"
    ), {"aid": app_id}).mappings().all()

    approve_count = sum(1 for v in votes if v["vote"] == "approve")
    voted_count = len(votes)

    if voted_count >= total:
        if total > 0 and approve_count / total >= pass_rate:
            db.execute(text("UPDATE promotion_applications SET status = 'approved', decided_at = NOW() WHERE id = :id"), {"id": app_id})
            db.execute(text("UPDATE consultants SET level = :level WHERE id = :cid"),
                       {"level": app["target_level"], "cid": app["consultant_id"]})
        else:
            db.execute(text("UPDATE promotion_applications SET status = 'rejected', decided_at = NOW() WHERE id = :id"), {"id": app_id})
        db.commit()
    elif total > 0 and approve_count / total >= pass_rate:
        db.execute(text("UPDATE promotion_applications SET status = 'approved', decided_at = NOW() WHERE id = :id"), {"id": app_id})
        db.execute(text("UPDATE consultants SET level = :level WHERE id = :cid"),
                   {"level": app["target_level"], "cid": app["consultant_id"]})
        db.commit()


# ────────── 人工直接晋级 ──────────

@router.post("/direct-promote")
def direct_promote(body: dict, db: Session = Depends(get_db), admin=Depends(get_admin_or_agent)):
    cid = body["consultant_id"]
    target_level = body["target_level"]
    remark = body.get("remark", "")

    t = db.query(Consultant).filter(Consultant.id == cid).first()
    if not t:
        raise HTTPException(404, "老师不存在")

    db.execute(text("UPDATE consultants SET level = :level WHERE id = :cid"),
               {"level": target_level, "cid": cid})

    year = date.today().year
    db.execute(text("""
        INSERT INTO promotion_applications (consultant_id, current_level, target_level, year,
            status, decided_at, decided_by, remark)
        VALUES (:cid, :cl, :tl, :y, 'approved', NOW(), :admin, :remark)
        ON CONFLICT (consultant_id, target_level, year) DO UPDATE SET
            status = 'approved', decided_at = NOW(), decided_by = :admin, remark = :remark
    """), {"cid": cid, "cl": t.level, "tl": target_level, "y": year,
           "admin": admin.id, "remark": remark or "人工直接晋级"})
    db.commit()
    return ok({"msg": f"已将 {t.name} 晋级为 {target_level}"})
