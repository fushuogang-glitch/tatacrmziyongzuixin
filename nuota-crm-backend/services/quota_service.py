# 下店名额计算
# 规则：每位顾问每月 (22 - 8 - 2) / 2 = 6 次
# 全月总名额 = 顾问人数 × 6
# 允许后台手动覆盖上限
from datetime import date
from typing import Dict

from sqlalchemy import extract, and_
from sqlalchemy.orm import Session

from models import Consultant, VisitBooking


DEFAULT_PER_CONSULTANT_SLOTS = 6

# 管理员可覆盖：{"YYYY-MM": 上限}
_monthly_override: Dict[str, int] = {}


def set_monthly_cap(year: int, month: int, cap: int) -> None:
    _monthly_override[f"{year:04d}-{month:02d}"] = cap


def get_monthly_cap(db: Session, year: int, month: int) -> int:
    key = f"{year:04d}-{month:02d}"
    if key in _monthly_override:
        return _monthly_override[key]
    n = db.query(Consultant).filter(Consultant.status == "active").count()
    return n * DEFAULT_PER_CONSULTANT_SLOTS


def count_used(db: Session, year: int, month: int) -> int:
    """已占用 = 本月 confirmed + completed 的预约数。"""
    return (
        db.query(VisitBooking)
        .filter(
            and_(
                extract("year", VisitBooking.confirmed_date) == year,
                extract("month", VisitBooking.confirmed_date) == month,
                VisitBooking.status.in_(["confirmed", "completed"]),
            )
        )
        .count()
    )


def quota_summary(db: Session, year: int, month: int) -> Dict[str, int]:
    cap = get_monthly_cap(db, year, month)
    used = count_used(db, year, month)
    return {
        "year": year,
        "month": month,
        "cap": cap,
        "used": used,
        "remaining": max(cap - used, 0),
    }


def has_quota(db: Session, target_date: date) -> bool:
    s = quota_summary(db, target_date.year, target_date.month)
    return s["remaining"] > 0
