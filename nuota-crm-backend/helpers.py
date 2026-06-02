# 杂项工具：编号/推荐码/标准返回
import random
import string
from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from models import Member


def gen_member_no(db: Session, year: Optional[int] = None) -> str:
    """生成学员编号：TT-YYYY-XXXX，按年份自增。"""
    year = year or date.today().year
    prefix = f"TT-{year}-"
    latest = (
        db.query(Member)
        .filter(Member.member_no.like(f"{prefix}%"))
        .order_by(Member.id.desc())
        .first()
    )
    seq = 1
    if latest and latest.member_no:
        try:
            seq = int(latest.member_no.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:04d}"


def gen_referral_code(length: int = 8) -> str:
    """生成大写字母+数字的推荐码。"""
    alphabet = string.ascii_uppercase + string.digits
    # 去掉易混淆字符
    for bad in "O0I1":
        alphabet = alphabet.replace(bad, "")
    return "".join(random.choices(alphabet, k=length))


def ok(data: Any = None, msg: str = "ok") -> Dict[str, Any]:
    """统一成功响应。"""
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str = "fail", code: int = 1, data: Any = None) -> Dict[str, Any]:
    """统一失败响应。"""
    return {"code": code, "msg": msg, "data": data}


def to_dict(obj: Any, fields: Optional[list] = None) -> Dict[str, Any]:
    """ORM 对象简易序列化。"""
    if obj is None:
        return {}
    if fields is None:
        fields = [c.name for c in obj.__table__.columns]
    out: Dict[str, Any] = {}
    for f in fields:
        v = getattr(obj, f, None)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        out[f] = v
    return out
