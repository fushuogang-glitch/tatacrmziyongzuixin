"""每日一念：每日黄历 / 每日一卦 / 月度经营启发."""
from datetime import date, datetime
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Member, MemberDailyProfile, DailyThoughtRecord, AdminUser, Consultant
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
    profile_type: Optional[str] = None
    auspicious_keyword: Optional[str] = None
    color_personality: Optional[str] = None
    mbti: Optional[str] = None
    bazi_analysis: Optional[str] = None
    teacher_notes: Optional[str] = None


ZODIACS = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
ZODIAC_TRIADS = [
    {"猴", "鼠", "龙"},
    {"蛇", "鸡", "牛"},
    {"虎", "马", "狗"},
    {"猪", "兔", "羊"},
]
ZODIAC_CLASHES = {
    "鼠": "马", "牛": "羊", "虎": "猴", "兔": "鸡", "龙": "狗", "蛇": "猪",
    "马": "鼠", "羊": "牛", "猴": "虎", "鸡": "兔", "狗": "龙", "猪": "蛇",
}
STEM_ELEMENT = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
    "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
BRANCH_ELEMENT = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
PROFILE_TYPE_LABELS = {
    "customer": "客户",
    "employee": "员工",
    "partner": "分公司伙伴",
    "boss": "公司老板",
}


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
    analysis = profile.bazi_analysis or "后台尚未录入专业八字命理测算"
    birth_hint = profile.bazi_text or (
        f"{profile.birth_date or '未填写生日'} {profile.birth_time or ''}".strip()
    )
    return (
        f"{month_key} 月度启发：本月关键词「{word}」。{theme}。"
        f"结合生辰信息（{birth_hint}），建议把经营动作放在“{word_tip}”上。"
        f"八字命理测算：{analysis}。"
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


def _admin_profile_out(db: Session, member: Member, profile: MemberDailyProfile) -> dict:
    data = _profile_out(profile)
    data["matching_report"] = _matching_report(db, member, profile)
    return data


def _zodiac_from_birth(birth_date: Optional[date]) -> Optional[str]:
    if not birth_date:
        return None
    return ZODIACS[(birth_date.year - 4) % 12]


def _day_stem(profile: MemberDailyProfile) -> Optional[str]:
    if not profile.bazi_text:
        return None
    parts = [p.strip() for p in profile.bazi_text.replace("，", " ").replace(",", " ").split() if p.strip()]
    if len(parts) >= 3 and parts[2]:
        stem = parts[2][0]
        return stem if stem in STEM_ELEMENT else None
    for ch in profile.bazi_text:
        if ch in STEM_ELEMENT:
            return ch
    return None


def _elements(profile: MemberDailyProfile) -> dict:
    counts = {k: 0 for k in ["木", "火", "土", "金", "水"]}
    text = profile.bazi_text or ""
    for ch in text:
        if ch in STEM_ELEMENT:
            counts[STEM_ELEMENT[ch]] += 1
        if ch in BRANCH_ELEMENT:
            counts[BRANCH_ELEMENT[ch]] += 1
    return counts


def _zodiac_score(a: Optional[str], b: Optional[str]) -> tuple[int, str]:
    if not a or not b:
        return 60, "属相资料不足，按中性匹配"
    if a == b:
        return 88, f"同属{a}，节奏相近"
    if ZODIAC_CLASHES.get(a) == b:
        return 42, f"{a}{b}相冲，合作需提前约定边界"
    for triad in ZODIAC_TRIADS:
        if a in triad and b in triad:
            return 92, f"{a}{b}三合，协作助力较强"
    return 72, f"{a}{b}无明显冲克，适合看八字整体"


def _stem_score(a: Optional[str], b: Optional[str]) -> tuple[int, str]:
    if not a or not b:
        return 60, "日柱天干资料不足，按中性匹配"
    ea, eb = STEM_ELEMENT[a], STEM_ELEMENT[b]
    if a == b:
        return 86, f"日主同为{a}{ea}，认知模式接近"
    if GENERATES.get(ea) == eb:
        return 90, f"{ea}生{eb}，一方能助推另一方"
    if GENERATES.get(eb) == ea:
        return 88, f"{eb}生{ea}，关系中有滋养之象"
    if CONTROLS.get(ea) == eb or CONTROLS.get(eb) == ea:
        return 52, f"{ea}{eb}有制化关系，适合明确权责"
    return 74, f"{ea}{eb}平稳，宜以事定人"


def _overall_score(a: MemberDailyProfile, b: MemberDailyProfile, zodiac_score: int, stem_score: int) -> tuple[int, str]:
    ae, be = _elements(a), _elements(b)
    total_a = sum(ae.values())
    total_b = sum(be.values())
    if not total_a or not total_b:
        return round(zodiac_score * 0.45 + stem_score * 0.55), "八字完整度不足，主要参考属相与日柱"
    shared = sum(min(ae[k], be[k]) for k in ae)
    balance = int(shared / max(total_a, total_b) * 100)
    score = round(zodiac_score * 0.25 + stem_score * 0.35 + balance * 0.40)
    strong = sorted(ae, key=ae.get, reverse=True)[0]
    other = sorted(be, key=be.get, reverse=True)[0]
    return score, f"五行重合度约{balance}%，一方偏{strong}，一方偏{other}"


def _match_one(member: Member, profile: MemberDailyProfile, other: Member, other_profile: MemberDailyProfile, relation: str) -> dict:
    za, zb = _zodiac_from_birth(profile.birth_date), _zodiac_from_birth(other_profile.birth_date)
    zodiac_score, zodiac_note = _zodiac_score(za, zb)
    sa, sb = _day_stem(profile), _day_stem(other_profile)
    stem_score, stem_note = _stem_score(sa, sb)
    overall_score, overall_note = _overall_score(profile, other_profile, zodiac_score, stem_score)
    return {
        "member_id": other.id,
        "name": other.name,
        "enterprise_name": other.enterprise_name,
        "role": other.role,
        "profile_type": other_profile.profile_type or "customer",
        "profile_type_label": PROFILE_TYPE_LABELS.get(other_profile.profile_type or "customer", other_profile.profile_type or "客户"),
        "relation": relation,
        "zodiac": {"self": za, "target": zb, "score": zodiac_score, "note": zodiac_note},
        "day_stem": {"self": sa, "target": sb, "score": stem_score, "note": stem_note},
        "overall": {"score": overall_score, "note": overall_note},
        "suggestion": _match_suggestion(overall_score, relation),
    }


def _match_suggestion(score: int, relation: str) -> str:
    if score >= 85:
        return f"{relation}匹配度高，适合重点协作与深度沟通。"
    if score >= 70:
        return f"{relation}匹配度平稳，建议按流程推进并加强复盘。"
    if score >= 55:
        return f"{relation}存在差异，适合提前明确目标、边界和节奏。"
    return f"{relation}冲突点较多，建议谨慎配对，由老师介入协调。"


def _candidate_profiles(db: Session, member: Member, profile: MemberDailyProfile) -> list[tuple[Member, MemberDailyProfile, str]]:
    q = (
        db.query(Member, MemberDailyProfile)
        .join(MemberDailyProfile, MemberDailyProfile.member_id == Member.id)
        .filter(Member.id != member.id, Member.status == "active")
    )
    rows = q.all()
    candidates = []
    for other, other_profile in rows:
        relation = None
        if profile.profile_type == "employee" and (other_profile.profile_type or "customer") in ("customer", "boss"):
            relation = "员工与客户"
        elif profile.profile_type in ("customer", "boss") and other_profile.profile_type == "employee":
            relation = "客户与员工"
        elif member.consultant_id and other.consultant_id == member.consultant_id:
            relation = "同组伙伴"
        if member.enterprise_id and other.enterprise_id == member.enterprise_id:
            relation = "企业内部"
        if relation:
            candidates.append((other, other_profile, relation))
    return candidates[:50]


def _boss_match(db: Session, member: Member, profile: MemberDailyProfile) -> Optional[dict]:
    boss = None
    if member.enterprise_id:
        from models.enterprise import Enterprise
        ent = db.query(Enterprise).filter(Enterprise.id == member.enterprise_id).first()
        if ent and ent.boss_member_id and ent.boss_member_id != member.id:
            boss = db.query(Member).filter(Member.id == ent.boss_member_id).first()
    if not boss and member.enterprise_name:
        boss = (
            db.query(Member)
            .filter(Member.id != member.id, Member.enterprise_name == member.enterprise_name, Member.role == "boss")
            .first()
        )
    if not boss:
        return None
    boss_profile = db.query(MemberDailyProfile).filter(MemberDailyProfile.member_id == boss.id).first()
    if not boss_profile:
        return None
    return _match_one(member, profile, boss, boss_profile, "与公司老板")


def _branch_partner_matches(db: Session, member: Member, profile: MemberDailyProfile) -> list[dict]:
    if not member.consultant_id:
        return []
    consultant = db.query(Consultant).filter(Consultant.id == member.consultant_id).first()
    if not consultant or not consultant.branch_id:
        return []
    branch_consultants = db.query(Consultant.id).filter(Consultant.branch_id == consultant.branch_id).all()
    consultant_ids = [c.id for c in branch_consultants]
    if not consultant_ids:
        return []
    rows = (
        db.query(Member, MemberDailyProfile)
        .join(MemberDailyProfile, MemberDailyProfile.member_id == Member.id)
        .filter(Member.id != member.id, Member.status == "active", Member.consultant_id.in_(consultant_ids))
        .limit(30)
        .all()
    )
    return [_match_one(member, profile, other, other_profile, "分公司伙伴") for other, other_profile in rows]


def _matching_report(db: Session, member: Member, profile: MemberDailyProfile) -> dict:
    direct = [_match_one(member, profile, other, other_profile, relation)
              for other, other_profile, relation in _candidate_profiles(db, member, profile)]
    branch = _branch_partner_matches(db, member, profile)
    boss = _boss_match(db, member, profile)
    direct.sort(key=lambda x: x["overall"]["score"], reverse=True)
    branch.sort(key=lambda x: x["overall"]["score"], reverse=True)
    return {
        "self": {
            "profile_type": profile.profile_type or "customer",
            "profile_type_label": PROFILE_TYPE_LABELS.get(profile.profile_type or "customer", "客户"),
            "zodiac": _zodiac_from_birth(profile.birth_date),
            "day_stem": _day_stem(profile),
            "elements": _elements(profile),
        },
        "customer_employee_matches": direct[:12],
        "branch_partner_matches": branch[:12],
        "boss_match": boss,
    }


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
    return ok(_admin_profile_out(db, member, profile))


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
    return ok(_admin_profile_out(db, member, profile), "每日一念资料已保存")
