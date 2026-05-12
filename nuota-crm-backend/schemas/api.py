# Pydantic schemas（输入/输出模型）
from datetime import date, datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, Field


# ========= 通用 =========
class RespOk(BaseModel):
    code: int = 0
    msg: str = "ok"
    data: Optional[Any] = None


# ========= 认证 =========
class WxLoginIn(BaseModel):
    code: str = Field(..., description="wx.login 获取的 code")


class AdminLoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    role: str
    expires_in_days: int
    user: Optional[Dict[str, Any]] = None


# ========= 学员 =========
class MemberRegisterIn(BaseModel):
    name: str
    phone: str
    enterprise_name: Optional[str] = None
    city: Optional[str] = None
    role: Optional[str] = None
    member_type: Optional[str] = "trial"
    referral_code: Optional[str] = None        # 绑定推荐关系
    openid: Optional[str] = None               # 可选：小程序登录已拿到的 openid


class MemberUpdateIn(BaseModel):
    name: Optional[str] = None
    enterprise_name: Optional[str] = None
    city: Optional[str] = None
    role: Optional[str] = None
    member_type: Optional[str] = None
    enroll_date: Optional[date] = None
    expire_date: Optional[date] = None
    status: Optional[str] = None


class MemberOut(BaseModel):
    id: int
    name: str
    phone: str
    enterprise_name: Optional[str] = None
    city: Optional[str] = None
    role: Optional[str] = None
    member_type: Optional[str] = None
    member_no: Optional[str] = None
    enroll_date: Optional[date] = None
    expire_date: Optional[date] = None
    referral_code: Optional[str] = None
    referred_by: Optional[int] = None
    status: Optional[str] = None
    face_bound: bool = False

    class Config:
        from_attributes = True


# ========= 人脸 =========
class FaceBindIn(BaseModel):
    face_base64: str = Field(..., description="人脸图 base64")


class FaceCheckinIn(BaseModel):
    session_id: int
    face_base64: str
    checkin_day: Optional[int] = None          # 不传则按场次 start_date 推算


# ========= 场次 =========
class SessionCreateIn(BaseModel):
    session_no: str
    start_date: date
    end_date: date
    location: Optional[str] = None
    city: Optional[str] = None
    capacity: int = 100


class SessionOut(BaseModel):
    id: int
    session_no: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    location: Optional[str]
    city: Optional[str]
    capacity: int
    enrolled: int
    status: str

    class Config:
        from_attributes = True


# ========= 推荐 =========
class ReferralOut(BaseModel):
    id: int
    referrer_id: int
    referee_id: int
    status: str
    reward_status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ========= 权益 =========
class RewardOut(BaseModel):
    id: int
    member_id: int
    source: Optional[str]
    status: str
    activate_time: Optional[datetime]
    expire_time: Optional[datetime]
    used_time: Optional[datetime]

    class Config:
        from_attributes = True


# ========= 预约 =========
class BookingApplyIn(BaseModel):
    reward_id: int
    preferred_date: date
    city: Optional[str] = None
    address: Optional[str] = None
    duration_days: int = 2
    remark: Optional[str] = None


class BookingConfirmIn(BaseModel):
    consultant_id: int
    confirmed_date: date


class BookingCompleteIn(BaseModel):
    member_rating: Optional[int] = None


class BookingOut(BaseModel):
    id: int
    member_id: int
    reward_id: Optional[int]
    consultant_id: Optional[int]
    preferred_date: Optional[date]
    confirmed_date: Optional[date]
    status: str
    duration_days: Optional[int]
    city: Optional[str]
    address: Optional[str]
    remark: Optional[str]
    member_rating: Optional[int]
    apply_time: Optional[datetime]

    class Config:
        from_attributes = True


# ========= 手册 =========
class HandbookSaveIn(BaseModel):
    day1_data: Optional[Dict[str, Any]] = None
    day2_data: Optional[Dict[str, Any]] = None
    day3_data: Optional[Dict[str, Any]] = None


# ========= 后台缴费 =========
class PaymentCreateIn(BaseModel):
    member_id: int
    amount: float
    pay_type: str = "annual"
    pay_status: str = "paid"
    remark: Optional[str] = None


# ========= 顾问 =========
class ConsultantIn(BaseModel):
    name: str
    phone: Optional[str] = None
    monthly_days: int = 14
    course_days: int = 8
    status: str = "active"


# ========= 名额 =========
class QuotaSetIn(BaseModel):
    year: int
    month: int
    cap: int
