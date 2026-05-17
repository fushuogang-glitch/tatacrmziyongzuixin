# JWT & 密码工具
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Member, AdminUser

# 学员端 JWT（走 Authorization: Bearer）
oauth2_member = OAuth2PasswordBearer(tokenUrl="/api/auth/wx-login", auto_error=False)
# 管理后台 JWT
oauth2_admin = OAuth2PasswordBearer(tokenUrl="/admin/auth/login", auto_error=False)


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except Exception:
        return False


def create_token(subject: str, role: str = "member", extra: Optional[Dict[str, Any]] = None) -> str:
    """生成 JWT。subject 一般是 member.id 或 admin.id。"""
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=settings.JWT_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"token 无效: {e}")


def get_current_member(
    token: Optional[str] = Depends(oauth2_member),
    db: Session = Depends(get_db),
) -> Member:
    """学员端依赖：解析 Bearer token -> Member 对象。"""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_token(token)
    if payload.get("role") != "member":
        raise HTTPException(status_code=401, detail="非学员身份")
    member_id = int(payload.get("sub", 0))
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=401, detail="学员不存在")
    return member


def get_current_admin(
    token: Optional[str] = Depends(oauth2_admin),
    db: Session = Depends(get_db),
) -> AdminUser:
    """后台依赖：解析 Bearer token -> AdminUser 对象。"""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_token(token)
    if payload.get("role") not in ("admin", "operator", "super_admin"):
        raise HTTPException(status_code=401, detail="非管理员身份")
    admin_id = int(payload.get("sub", 0))
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id, AdminUser.status == "active").first()
    if not admin:
        raise HTTPException(status_code=401, detail="账号不存在或已停用")
    return admin


class CurrentUser:
    """统一身份：admin或consultant都能用"""
    def __init__(self, role: str, user_id: int, consultant_id: Optional[int] = None, obj: Any = None):
        self.role = role                # 'admin'/'super_admin'/'operator'/'consultant'
        self.user_id = user_id
        self.consultant_id = consultant_id  # 老师才有
        self.obj = obj                  # 原始 AdminUser 或 Consultant 对象

    @property
    def is_admin(self) -> bool:
        return self.role in ('admin', 'operator', 'super_admin')

    @property
    def is_consultant(self) -> bool:
        return self.role == 'consultant'


def get_current_admin_or_consultant(
    token: Optional[str] = Depends(oauth2_admin),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """后台统一鉴权：admin 和 consultant 都可通过"""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_token(token)
    role = payload.get("role", "")
    uid = int(payload.get("sub", 0))

    if role in ("admin", "operator", "super_admin"):
        admin = db.query(AdminUser).filter(AdminUser.id == uid, AdminUser.status == "active").first()
        if not admin:
            raise HTTPException(status_code=401, detail="账号不存在或已停用")
        return CurrentUser(role=role, user_id=uid, obj=admin)

    if role == "consultant":
        from models.booking import Consultant
        c = db.query(Consultant).filter(Consultant.id == uid).first()
        if not c:
            raise HTTPException(status_code=401, detail="老师不存在")
        return CurrentUser(role='consultant', user_id=uid, consultant_id=uid, obj=c)

    raise HTTPException(status_code=401, detail="身份无效")
