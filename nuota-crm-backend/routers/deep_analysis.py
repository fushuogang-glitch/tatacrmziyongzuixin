"""会员深度分析 + 老师人才模型分析 路由 - 2026-06-02
- 老师录入端（JWT）：录原始资料 + 读结果
- 塔才回写端（X-Api-Key=taicai）：拉待分析 + 回写结果
- 权限：老师人才分析 老师不可见/分公司管理员看本店/超管全部
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import (
    MemberDeepAnalysis, ConsultantTalentAnalysis, Member, Consultant,
)
from models.handbook import AdminUser
from utils.auth import get_current_admin
from utils.agent_auth import AgentAuth, get_agent_auth, check_agent_permission

router = APIRouter(tags=["深度分析"])


# ═══════════════ Pydantic ═══════════════
class RawInput(BaseModel):
    raw_text: Optional[str] = None
    raw_images: Optional[List[str]] = None


class AnalysisResult(BaseModel):
    color_analysis: Optional[dict] = None
    mbti: Optional[dict] = None
    bazi: Optional[dict] = None
    special_habits: Optional[str] = None
    service_guide: Optional[str] = None      # 客户用
    teaching_guide: Optional[str] = None     # 老师用
    summary: Optional[str] = None
    matched_members: Optional[list] = None   # 老师用


def _ok(data=None, msg="ok"):
    return {"code": 0, "msg": msg, "data": data}


def _ser(o):
    if o is None:
        return None
    return {c.name: getattr(o, c.name) for c in o.__table__.columns}


# ═══════════════ 老师/管理员录入端（JWT）═══════════════

@router.post("/admin/members/{member_id}/deep-analysis")
def input_member_analysis(
    member_id: int, body: RawInput,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """录入/更新客户原始资料 → 状态置 pending（等塔才分析）"""
    m = db.query(Member).filter(Member.id == member_id).first()
    if not m:
        raise HTTPException(404, "会员不存在")
    rec = db.query(MemberDeepAnalysis).filter(MemberDeepAnalysis.member_id == member_id).first()
    if not rec:
        rec = MemberDeepAnalysis(member_id=member_id, branch_id=getattr(m, "branch_id", None), created_by=admin.id)
        db.add(rec)
    rec.raw_text = body.raw_text
    rec.raw_images = body.raw_images
    rec.status = "pending"
    rec.updated_at = datetime.utcnow()
    db.commit(); db.refresh(rec)
    return _ok(_ser(rec))


@router.get("/admin/members/{member_id}/deep-analysis")
def get_member_analysis(
    member_id: int,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """读客户深度分析（展示）"""
    rec = db.query(MemberDeepAnalysis).filter(MemberDeepAnalysis.member_id == member_id).first()
    return _ok(_ser(rec))


@router.post("/admin/consultants/{consultant_id}/talent-analysis")
def input_consultant_analysis(
    consultant_id: int, body: RawInput,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """录入/更新老师原始资料 → pending"""
    c = db.query(Consultant).filter(Consultant.id == consultant_id).first()
    if not c:
        raise HTTPException(404, "老师不存在")
    rec = db.query(ConsultantTalentAnalysis).filter(ConsultantTalentAnalysis.consultant_id == consultant_id).first()
    if not rec:
        rec = ConsultantTalentAnalysis(consultant_id=consultant_id, branch_id=getattr(c, "branch_id", None), created_by=admin.id)
        db.add(rec)
    rec.raw_text = body.raw_text
    rec.raw_images = body.raw_images
    rec.status = "pending"
    rec.updated_at = datetime.utcnow()
    db.commit(); db.refresh(rec)
    return _ok(_ser(rec))


@router.get("/admin/consultants/{consultant_id}/talent-analysis")
def get_consultant_analysis(
    consultant_id: int,
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """读老师人才分析·三级权限：老师不可见/分公司管理员看本店/超管全部"""
    role = getattr(admin, "role", None)
    if role not in ("admin", "operator", "super_admin"):
        raise HTTPException(403, "无权查看老师人才分析")
    rec = db.query(ConsultantTalentAnalysis).filter(ConsultantTalentAnalysis.consultant_id == consultant_id).first()
    if not rec:
        return _ok(None)
    # 分公司管理员只能看本店
    if role in ("admin", "operator"):
        admin_branch = getattr(admin, "branch_id", None)
        if admin_branch and rec.branch_id and rec.branch_id != admin_branch:
            raise HTTPException(403, "仅可查看本分公司老师分析")
    return _ok(_ser(rec))


@router.get("/admin/talent-analysis")
def list_talent_analysis(
    db: DBSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """老师人才分析列表·三级权限"""
    role = getattr(admin, "role", None)
    if role not in ("admin", "operator", "super_admin"):
        raise HTTPException(403, "无权查看")
    q = db.query(ConsultantTalentAnalysis)
    if role in ("admin", "operator"):
        admin_branch = getattr(admin, "branch_id", None)
        if admin_branch:
            q = q.filter(ConsultantTalentAnalysis.branch_id == admin_branch)
    rows = q.order_by(desc(ConsultantTalentAnalysis.updated_at)).all()
    out = []
    for r in rows:
        c = db.query(Consultant).filter(Consultant.id == r.consultant_id).first()
        d = _ser(r)
        d["consultant_name"] = getattr(c, "name", None) if c else None
        out.append(d)
    return _ok(out)


# ═══════════════ 塔才回写端（X-Api-Key）═══════════════

def _require_taicai(request: Request, agent: Optional[AgentAuth] = Depends(get_agent_auth)):
    if agent is None:
        raise HTTPException(401, "缺少 X-Api-Key")
    check_agent_permission(request, agent)
    return agent


@router.get("/agent/deep-analysis/pending")
def agent_pending(request: Request, agent: AgentAuth = Depends(_require_taicai), db: DBSession = Depends(get_db)):
    """塔才拉所有待分析（客户+老师）"""
    members = db.query(MemberDeepAnalysis).filter(MemberDeepAnalysis.status == "pending").all()
    consultants = db.query(ConsultantTalentAnalysis).filter(ConsultantTalentAnalysis.status == "pending").all()
    return _ok({
        "members": [_ser(m) for m in members],
        "consultants": [_ser(c) for c in consultants],
    })


@router.post("/agent/deep-analysis/member/{member_id}/result")
def agent_member_result(member_id: int, body: AnalysisResult, request: Request,
                        agent: AgentAuth = Depends(_require_taicai), db: DBSession = Depends(get_db)):
    """塔才回写客户分析结果"""
    rec = db.query(MemberDeepAnalysis).filter(MemberDeepAnalysis.member_id == member_id).first()
    if not rec:
        raise HTTPException(404, "未找到该客户分析记录（需先由老师录入原始资料）")
    rec.color_analysis = body.color_analysis
    rec.mbti = body.mbti
    rec.bazi = body.bazi
    if body.special_habits is not None:
        rec.special_habits = body.special_habits
    rec.service_guide = body.service_guide
    rec.summary = body.summary
    rec.status = "analyzed"
    rec.analyzed_by = agent.agent_name
    rec.analyzed_at = datetime.utcnow()
    db.commit(); db.refresh(rec)
    return _ok(_ser(rec))


@router.post("/agent/deep-analysis/consultant/{consultant_id}/result")
def agent_consultant_result(consultant_id: int, body: AnalysisResult, request: Request,
                            agent: AgentAuth = Depends(_require_taicai), db: DBSession = Depends(get_db)):
    """塔才回写老师分析结果 + 匹配客户名单"""
    rec = db.query(ConsultantTalentAnalysis).filter(ConsultantTalentAnalysis.consultant_id == consultant_id).first()
    if not rec:
        raise HTTPException(404, "未找到该老师分析记录")
    rec.color_analysis = body.color_analysis
    rec.mbti = body.mbti
    rec.bazi = body.bazi
    if body.special_habits is not None:
        rec.special_habits = body.special_habits
    rec.teaching_guide = body.teaching_guide
    rec.summary = body.summary
    rec.matched_members = body.matched_members
    rec.status = "analyzed"
    rec.analyzed_by = agent.agent_name
    rec.analyzed_at = datetime.utcnow()
    db.commit(); db.refresh(rec)
    return _ok(_ser(rec))
