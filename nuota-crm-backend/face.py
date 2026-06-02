# 人脸绑定（学员端）
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Member
from schemas.api import FaceBindIn
from services.face_service import face_service
from utils.auth import get_current_member
from utils.helpers import ok


router = APIRouter(prefix="/api/face", tags=["face"])


@router.post("/bind")
def bind_face(body: FaceBindIn, db: Session = Depends(get_db),
              current: Member = Depends(get_current_member)):
    """首次绑定人脸：调用腾讯云 CreatePerson/CreateFace，保存 face_token。"""
    r = face_service.bind(current.id, body.face_base64)
    if not r.get("ok"):
        raise HTTPException(status_code=400, detail=r.get("msg", "人脸绑定失败"))

    current.face_token = r["face_token"]
    db.commit()
    return ok({"face_bound": True, "msg": r.get("msg")})


@router.get("/status")
def face_status(current: Member = Depends(get_current_member)):
    return ok({"face_bound": bool(current.face_token)})
