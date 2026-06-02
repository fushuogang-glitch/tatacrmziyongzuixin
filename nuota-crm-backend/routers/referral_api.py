"""推荐码验证 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Member
from models.booking import Consultant
from utils.helpers import ok

router = APIRouter(prefix="/api/referral", tags=["referral"])


@router.get("/verify")
def verify_referral_code(code: str, db: Session = Depends(get_db)):
    """验证推荐码，返回推荐来源信息"""
    if not code or len(code) < 3:
        raise HTTPException(400, "推荐码格式错误")
    
    # 1. 查会员推荐码
    member = db.query(Member).filter(Member.referral_code == code).first()
    if member:
        return ok({
            "valid": True,
            "source": "member",
            "source_name": member.name,
            "enterprise_name": member.enterprise_name or "",
            "hint": f"由会员 {member.name} 推荐"
        })
    
    # 2. 查老师推荐码
    consultant = db.query(Consultant).filter(Consultant.referral_code == code).first()
    if consultant:
        return ok({
            "valid": True,
            "source": "consultant",
            "source_name": consultant.name,
            "hint": f"由塔塔老师 {consultant.name} 推荐"
        })
    
    raise HTTPException(400, "推荐码无效")
