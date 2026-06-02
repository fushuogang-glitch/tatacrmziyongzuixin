# 课程手册
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Handbook, Member, AdminUser
from schemas.api import HandbookSaveIn
from utils.auth import get_current_member, get_current_admin
from utils.helpers import ok, to_dict


router = APIRouter(prefix="/api/handbooks", tags=["handbooks"])
admin_router = APIRouter(prefix="/admin/handbooks", tags=["admin-handbooks"])


def _get_or_create(db: Session, member_id: int, session_id: int) -> Handbook:
    h = (
        db.query(Handbook)
        .filter(Handbook.member_id == member_id, Handbook.session_id == session_id)
        .first()
    )
    if not h:
        h = Handbook(member_id=member_id, session_id=session_id)
        db.add(h)
        db.flush()
    return h


@router.get("/{session_id}")
def get_handbook(session_id: int, db: Session = Depends(get_db),
                 current: Member = Depends(get_current_member)):
    h = _get_or_create(db, current.id, session_id)
    db.commit()
    return ok(to_dict(h))


@router.put("/{session_id}")
def save_handbook(session_id: int, body: HandbookSaveIn,
                  db: Session = Depends(get_db),
                  current: Member = Depends(get_current_member)):
    h = _get_or_create(db, current.id, session_id)
    if body.day1_data is not None:
        h.day1_data = body.day1_data
    if body.day2_data is not None:
        h.day2_data = body.day2_data
    if body.day3_data is not None:
        h.day3_data = body.day3_data

    if h.day1_data and h.day2_data and h.day3_data:
        h.is_complete = True
    db.commit()
    db.refresh(h)
    return ok(to_dict(h))


# ---- 管理端：签字确认 ----
@admin_router.put("/{hid}/sign")
def admin_sign(hid: int, consultant_id: int | None = None,
               db: Session = Depends(get_db),
               _: AdminUser = Depends(get_current_admin)):
    h = db.query(Handbook).filter(Handbook.id == hid).first()
    if not h:
        raise HTTPException(status_code=404, detail="手册不存在")
    h.sign_time = datetime.utcnow()
    if consultant_id:
        h.consultant_id = consultant_id
    h.is_complete = True
    db.commit()
    return ok(to_dict(h))
