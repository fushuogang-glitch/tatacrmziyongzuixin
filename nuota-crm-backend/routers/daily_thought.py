"""每日一念：每日黄历 / 每日一卦 / 月度经营启发."""
from datetime import date, datetime
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Member, MemberDailyProfile, DailyThoughtRecord, AdminUser
from utils.auth import get_current_member, get_admin_or_agent
from utils.helpers import ok, to_dict


router = APIRouter(tags=["daily-thought"])
api_router = APIRouter(prefix="/api/daily-thought", tags=["daily-thought"])
admin_router = APIRouter(prefix="/admin/daily-thought", tags=["daily-thought-admin"])

WORDS = [
    ("生发", "今日宜顺势而为，先整理，再推进。"),
    ("笃行", "少说多做，稳住节奏，成果自然显现。"),
    ("聚气", "把注意力收回来，聚焦一件真正重要的事。"),
    ("明心", "看清自己的判断，也看见团队的真实状态。"),
    ("和合", "适合沟通、复盘、修补关系，先求同再求进。"),
    ("启新", "适合开启新计划，但要留出试错空间。"),
    ("守正", "不急于扩张，先把标准和流程守稳。"),
    ("丰盈", "关注现金流、客户体验与复购机会。"),
    ("长青", "把短期动作放进长期主义里。"),
    ("照见", "今天适合复盘数据，找到真正的问题。"),
]

HEXAGRAMS = [
    ("乾为天", "自强不息，宜主动推进关键事项。"),
    ("坤为地", "厚德载物，宜稳住团队与客户关系。"),
    ("风雷益", "利于增益，适合做客户服务与价值交付。"),
    ("山火贲", "修饰有度，适合优化门店呈现与品牌表达。"),
    ("水火既济", "阶段完成，宜复盘沉淀，不宜冒进。"),
    ("地山谦", "谦逊受益，适合请教、协作、打磨细节。"),
]

GOOD = [
    "沟通复盘", "客户回访", "签约洽谈", "学习培训", "整理账目",
    "团队共创", "内容发布", "产品优化", "排期确认", "门店巡检",
]

AVOID = [
    "仓促承诺", "情绪决策", "忽略现金流", "临时变更流程", "过度扩张",
    "跳过复盘", "信息不透明", "拖延跟进", "重复返工", "单点依赖",
]

MONTH_THEMES = [
    "稳现金流，重客户体验",
    "先标准化，再复制增长",
    "适合做团队训练与流程升级",
    "关注复购、转介绍与老客激活",
    "以产品呈现带动品牌信任",
    "用数据复盘替代感觉判断",
]


class DailyProfileIn(BaseModel):
    birth_date: Optional[date] = None
    birth_time: Optional[str] = None
    bazi_text: Optional[str] = None


class AdminDailyProfileIn(DailyProfileIn):
    auspicious_keyword: Optional[str] = None
    color_personality: Optional[str] = None
    mbti: Optional[str] = None
    teacher_notes: Optional[str] = None


def _idx(seed: str, modulo: int) -> int:
    raw = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(raw[:8], 16) % modulo


def _profile_for(db: Session, member_id: int) -> MemberDailyProfile:
    profile = db.query(MemberDailyProfile).filter(MemberDailyProfile.member_id == member_id).first()
    if not profile:
        profile = MemberDailyProfile(member_id=member_id)
        db.add(profile)
        db.flush()
    return profile


def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def _generate_monthly_fortune(member: Member, profile: MemberDailyProfile, month_key: str) -> str:
    seed = f"{member.id}:{profile.birth_date}:{profile.birth_time}:{profile.bazi_text}:{month_key}"
    theme = MONTH_THEMES[_idx(seed + ":theme", len(MONTH_THEMES))]
    word, word_tip = WORDS[_idx(seed + ":word", len(WORDS))]
    color = profile.color_personality or "待老师补充颜色性格"
    mbti = profile.mbti or "待老师补充 MBTI"
    birth_hint = profile.bazi_text or (
        f"{profile.birth_date or '未填写生日'} {profile.birth_time or ''}".strip()
    )
    return (
        f"{month_key} 月度启发：本月关键词「{word}」。{theme}。"
        f"结合生辰信息（{birth_hint}），建议把经营动作放在“{word_tip}”上。"
        f"颜色性格：{color}；MBTI：{mbti}。"
        "以上内容仅作文化娱乐与经营复盘启发，不作为决策或投资依据。"
    )


def _daily_record_for(db: Session, member: Member, profile: MemberDailyProfile) -> DailyThoughtRecord:
    today = date.today()
    record = (
        db.query(DailyThoughtRecord)
        .filter(DailyThoughtRecord.member_id == member.id, DailyThoughtRecord.record_date == today)
        .first()
    )
    if record:
        return record
    seed = f"{member.id}:{today.isoformat()}:{profile.bazi_text or ''}:{profile.birth_date or ''}"
    word, meaning = WORDS[_idx(seed + ":word", len(WORDS))]
    hexagram, hexagram_meaning = HEXAGRAMS[_idx(seed + ":hex", len(HEXAGRAMS))]
    good_items = [GOOD[_idx(seed + f":good:{i}", len(GOOD))] for i in range(3)]
    avoid_items = [AVOID[_idx(seed + f":avoid:{i}", len(AVOID))] for i in range(3)]
    # 去重后保序
    good_items = list(dict.fromkeys(good_items))
    avoid_items = list(dict.fromkeys(avoid_items))
    record = DailyThoughtRecord(
        member_id=member.id,
        record_date=today,
        word=profile.auspicious_keyword or word,
        hexagram=hexagram,
        meaning=f"{meaning} {hexagram_meaning}",
        almanac_good="、".join(good_items),
        almanac_avoid="、".join(avoid_items),
    )
    db.add(record)
    db.flush()
    return record


def _profile_out(profile: MemberDailyProfile) -> dict:
    return to_dict(profile) if profile else {}


@api_router.get("/today")
def today_thought(current: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    profile = _profile_for(db, current.id)
    month_key = _current_month()
    if profile.monthly_fortune_month != month_key:
        profile.monthly_fortune_month = month_key
        profile.monthly_fortune = _generate_monthly_fortune(current, profile, month_key)
    record = _daily_record_for(db, current, profile)
    db.commit()
    return ok({
        "date": record.record_date.isoformat(),
        "word": record.word,
        "hexagram": record.hexagram,
        "meaning": record.meaning,
        "almanac": {
            "good": record.almanac_good,
            "avoid": record.almanac_avoid,
        },
        "profile": _profile_out(profile),
        "monthly_fortune": profile.monthly_fortune,
        "disclaimer": "每日一念仅作文化娱乐与经营启发参考。",
    })


@api_router.put("/profile")
def save_my_profile(body: DailyProfileIn, current: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    profile = _profile_for(db, current.id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    profile.monthly_fortune_month = _current_month()
    profile.monthly_fortune = _generate_monthly_fortune(current, profile, profile.monthly_fortune_month)
    db.commit()
    db.refresh(profile)
    return ok(_profile_out(profile), "每日一念资料已保存")


@admin_router.get("/members/{member_id}/profile")
def admin_get_profile(member_id: int, db: Session = Depends(get_db), _: AdminUser = Depends(get_admin_or_agent)):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(404, "会员不存在")
    profile = _profile_for(db, member_id)
    if not profile.monthly_fortune:
        profile.monthly_fortune_month = _current_month()
        profile.monthly_fortune = _generate_monthly_fortune(member, profile, profile.monthly_fortune_month)
        db.commit()
    return ok(_profile_out(profile))


@admin_router.put("/members/{member_id}/profile")
def admin_save_profile(
    member_id: int,
    body: AdminDailyProfileIn,
    db: Session = Depends(get_db),
    current: AdminUser = Depends(get_admin_or_agent),
):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(404, "会员不存在")
    profile = _profile_for(db, member_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    profile.updated_by = getattr(current, "id", None)
    profile.monthly_fortune_month = _current_month()
    profile.monthly_fortune = _generate_monthly_fortune(member, profile, profile.monthly_fortune_month)
    db.commit()
    db.refresh(profile)
    return ok(_profile_out(profile), "每日一念资料已保存")
