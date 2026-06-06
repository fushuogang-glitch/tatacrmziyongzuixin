from utils.auth import get_current_member
# 协议签约路由 —— 强制签约审计
import hashlib
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Member, UserAgreement


# 当前协议版本（改版时升级，旧用户需重签）
CURRENT_AGREEMENT_VERSION = "v1.0"
EFFECTIVE_DATE = "2026-05-13"

AGREEMENT_CONTENT = """嘉塔诺塔会员服务协议

甲方：上海嘉塔诺塔管理咨询有限公司（塔塔咨询）
乙方：注册并使用本小程序的会员用户

第一条 协议确认
1.1 会员通过点击同意本协议、完成注册流程，即视为已充分阅读、理解并同意本协议全部条款。
1.2 本协议自会员点击同意之日起生效，构成具有法律约束力的电子合同。

第二条 服务内容
2.1 塔塔咨询为会员提供：
（1）专案服务：门店诊断、品项搭建、团队培训、品牌升级等
（2）课程服务：录播课程购买、线下场次报名
（3）会员权益：根据会员等级享受相应权益

第三条 会员等级与权益
3.1 会员等级根据年度累计消费动态调整，共设九个等级。
3.2 银卡及以上：推荐学员可获服务升级权益。
3.3 金卡及以上：享有专案服务优先排期权。
3.4 黑金卡：享有最高优先排期权及专属顾问服务。

第四条 付费与退款
4.1 会员一旦完成付费，所购买课程、服务即开通使用权限。
4.2 课程体验价每人仅限购买一次。
4.3 已开通的录播课程、已发生的专案服务，原则上不予退款。

第五条 会员义务
5.1 提供真实有效的注册信息，不得冒用他人身份。
5.2 不得将账号、课程内容转借、转售给第三方。

第六条 知识产权
6.1 本小程序及全部课程内容、方法论、品牌资料等知识产权归塔塔咨询所有。

第七条 隐私保护
7.1 严格保护会员个人信息，不向第三方泄露。

第八条 协议变更
8.1 塔塔咨询有权根据业务发展调整本协议条款。

第九条 争议解决
9.1 本协议适用中华人民共和国法律。
9.2 因本协议产生的争议，提交甲方所在地有管辖权的人民法院解决。

第十条 附则
10.1 本协议未尽事宜，参照相关法律法规及行业惯例处理。
10.2 本协议解释权归塔塔咨询所有。
"""

AGREEMENT_HASH = hashlib.sha256(AGREEMENT_CONTENT.encode("utf-8")).hexdigest()


router = APIRouter(prefix="/api/v1/agreements", tags=["协议签约"])


class SignBody(BaseModel):
    member_id: Optional[int] = None
    signature: Optional[str] = None  # 手写签名 base64（可选）


def _resolve_member_id(current: Member, requested_member_id: Optional[int] = None) -> int:
    if requested_member_id and requested_member_id != current.id:
        raise HTTPException(403, "无权访问其他会员数据")
    return current.id


@router.get("/current")
def get_current_agreement():
    """获取当前生效的协议内容"""
    return {
        "code": 0,
        "data": {
            "version": CURRENT_AGREEMENT_VERSION,
            "effective_date": EFFECTIVE_DATE,
            "hash": AGREEMENT_HASH,
            "content": AGREEMENT_CONTENT,
        }
    }


@router.get("/check")
def check_agreement_signed(member_id: Optional[int] = None, db: Session = Depends(get_db), current = Depends(get_current_member)):
    member_id = _resolve_member_id(current, member_id)
    """检查用户是否已签约最新版协议"""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(404, "会员不存在")
    signed = (
        member.agreement_signed
        and member.agreement_version == CURRENT_AGREEMENT_VERSION
    )
    return {
        "code": 0,
        "data": {
            "signed": signed,
            "current_version": CURRENT_AGREEMENT_VERSION,
            "user_version": member.agreement_version,
            "signed_at": member.agreement_signed_at.isoformat() if member.agreement_signed_at else None,
        }
    }


@router.post("/sign")
def sign_agreement(
    body: SignBody, request: Request, db: Session = Depends(get_db),
    current: Member = Depends(get_current_member)
):
    """会员签约协议"""
    mid = _resolve_member_id(current, body.member_id)
    member = db.query(Member).filter(Member.id == mid).first()
    if not member:
        raise HTTPException(404, "会员不存在")

    client_ip = request.client.host if request.client else None
    client_ua = request.headers.get("user-agent")

    # 写入审计表
    audit = UserAgreement(
        member_id=mid,
        agreement_version=CURRENT_AGREEMENT_VERSION,
        agreement_hash=AGREEMENT_HASH,
        signed_at=datetime.now(),
        client_ip=client_ip,
        client_ua=client_ua,
        signature=body.signature,
        is_valid=True,
    )
    db.add(audit)

    # 更新会员主表
    member.agreement_signed = True
    member.agreement_version = CURRENT_AGREEMENT_VERSION
    member.agreement_signed_at = datetime.now()

    db.commit()
    db.refresh(audit)
    return {
        "code": 0,
        "msg": "签约成功",
        "data": {
            "id": audit.id,
            "version": CURRENT_AGREEMENT_VERSION,
            "signed_at": audit.signed_at.isoformat(),
        }
    }


@router.get("/history")
def agreement_history(member_id: Optional[int] = None, db: Session = Depends(get_db), current = Depends(get_current_member)):
    member_id = _resolve_member_id(current, member_id)
    """签约历史"""
    records = db.query(UserAgreement).filter(
        UserAgreement.member_id == member_id
    ).order_by(UserAgreement.signed_at.desc()).all()
    return {
        "code": 0,
        "data": [
            {
                "id": r.id,
                "version": r.agreement_version,
                "signed_at": r.signed_at.isoformat(),
                "client_ip": r.client_ip,
                "is_valid": r.is_valid,
            } for r in records
        ]
    }
