"""八字排盘引擎 v1 — 纯算法（A方案）
输入：出生年月日(+可选时辰) → 输出四柱、当日/流月运势、宜忌
不依赖外部库，基于干支历法计算。AI润色(B方案)由调用方可选叠加。
"""
from datetime import date, datetime, timedelta

TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
WUXING_GAN = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
              "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
WUXING_ZHI = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
              "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
SHENGXIAO = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

# 干支相生：木→火→土→金→水→木
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
# 相克：木克土 土克水 水克火 火克金 金克木
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 基准：1900-01-31 为甲辰日（公历）干支日序基准点之一，用儒略日法更稳
def _jdn(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def ganzhi_day(d: date):
    """某公历日的干支（日柱）。JDN 对 60 取模校准。"""
    jdn = _jdn(d.year, d.month, d.day)
    # 校准：2000-01-07 为甲子日(JDN=2451551)
    idx = (jdn - 2451551) % 60
    if idx < 0:
        idx += 60
    return TIANGAN[idx % 10] + DIZHI[idx % 12]


def ganzhi_year(y: int):
    """年柱（按立春简化为公历年，足够运营用）。1984=甲子年。"""
    idx = (y - 1984) % 60
    if idx < 0:
        idx += 60
    return TIANGAN[idx % 10] + DIZHI[idx % 12]


def ganzhi_month(y: int, m: int):
    """月柱（简化：以公历月对应地支，年干推月干）。"""
    # 寅月起正月(寅=2月)；这里用公历月近似地支
    zhi_idx = (m + 1) % 12  # 1月→丑(1) 2月→寅(2)... 近似
    # 年干推月干：甲己之年丙作首
    ygan = (y - 1984) % 10
    if ygan < 0:
        ygan += 10
    month_gan_start = {0: 2, 1: 4, 2: 6, 3: 8, 4: 0, 5: 2, 6: 4, 7: 6, 8: 8, 9: 0}  # 甲己丙起
    gan_idx = (month_gan_start[ygan] + (m - 1)) % 10
    return TIANGAN[gan_idx] + DIZHI[zhi_idx]


def liuyue(d: date):
    """当前流月干支"""
    return ganzhi_month(d.year, d.month)


def liunian(d: date):
    """当前流年干支"""
    return ganzhi_year(d.year)


def _wuxing_of(gz: str):
    return WUXING_GAN.get(gz[0], ""), WUXING_ZHI.get(gz[1], "")


def paipan(birth: date, birth_hour: int = None):
    """排四柱"""
    year_gz = ganzhi_year(birth.year)
    month_gz = ganzhi_month(birth.year, birth.month)
    day_gz = ganzhi_day(birth)
    hour_gz = None
    if birth_hour is not None:
        zhi_idx = ((birth_hour + 1) // 2) % 12
        dgan = TIANGAN.index(day_gz[0])
        hgan = (dgan * 2 + zhi_idx) % 10
        hour_gz = TIANGAN[hgan] + DIZHI[zhi_idx]
    day_master = day_gz[0]
    dm_wx = WUXING_GAN[day_master]
    return {
        "year": year_gz, "month": month_gz, "day": day_gz, "hour": hour_gz,
        "day_master": day_master, "day_master_wuxing": dm_wx,
        "shengxiao": SHENGXIAO[(birth.year - 1900) % 12],
        "pillars_text": f"{year_gz} {month_gz} {day_gz}" + (f" {hour_gz}" if hour_gz else ""),
    }


# 当日运势：日柱五行 与 命主日主五行 生克关系 → 吉凶倾向
_FORTUNE_LEVEL = {
    "same": ("比和", "今日与你气场相合，宜按计划稳步推进，贵人运平稳。"),
    "sheng_me": ("印星生身", "今日有贵人/长辈相助之象，宜学习、签约、寻求支持。"),
    "me_sheng": ("食伤泄秀", "今日宜表达、营销、对外沟通，创意旺，忌过度消耗。"),
    "me_ke": ("财星", "今日财气活跃，宜谈生意、收款、推进成交，注意理性消费。"),
    "ke_me": ("官杀克身", "今日压力偏大，宜守不宜攻，谨慎决策，避免冲突与冒险。"),
}

GOOD_POOL = ["签约", "洽谈", "出行", "开业", "营销", "面谈", "学习", "理财", "美容护理", "拜访客户"]
AVOID_POOL = ["冲动消费", "争执", "重大决策", "高风险投资", "熬夜", "轻信他人"]

WUXING_COLOR = {
    "木": {"name": "青绿系", "hex": "#3CB371"},
    "火": {"name": "红橙系", "hex": "#E94F4F"},
    "土": {"name": "黄棕系", "hex": "#D9A441"},
    "金": {"name": "白金系", "hex": "#C9A86A"},
    "水": {"name": "黑蓝系", "hex": "#2C3E70"},
}

DAILY_QUOTES = [
    "一览众山小",
    "日出东方，万物可期",
    "停下来，就是风景",
    "美丽的阳光，是免费的",
    "心宽似海，路自然宽",
    "慢慢来，比较快",
    "山高自有客行路",
    "心若安，何处不归途",
    "清风徐来，水波不兴",
    "向阳而生，逐光而行",
    "云在青天，水在瓶",
    "万物各有时，急不得",
    "守得云开，见月明",
    "花未全开，月未圆",
    "心中有光，慢食三餐",
    "所遇皆温柔，所求皆如愿",
    "春有百花秋有月",
    "行至水穷处，坐看云起时",
    "风物长宜放眼量",
    "不疾不徐，自有芳华",
    "心若向阳，无谓悲伤",
    "岁月不居，时节如流",
    "素履以往，一苇以航",
    "人间值得，未来可期",
    "好饭不怕晚，好事不怕慢",
    "眼里有光，心中有暖",
    "半山腰太挤，要去山顶看看",
    "凡是过往，皆为序章",
    "落日归山海，山海藏深意",
    "择一事，终一生",
    "愿有岁月可回首",
    "心安即是归处",
    "简单的事重复做，你就是赢家",
    "你若盛开，清风自来",
    "活成一束光，照亮自己",
    "把日子过成诗",
    "岁岁常欢愉，万事皆胜意",
    "所念皆所愿，所行化坦途",
    "愿你三冬暖，愿你春不寒",
    "细水长流，方能行远",
    "静水流深，沧笙踏歌",
    "不忘初心，方得始终",
    "春风十里，不如自己争气",
    "心宽一寸，路宽一丈",
    "越努力，越幸运",
    "花开半夏，岁月静好",
    "愿你出走半生，归来仍少年",
    "心若计较，处处都有怨言",
    "知足常乐，能忍自安",
    "千里之行，始于足下",
    "一日之计在于晨",
    "凡心所向，素履以往",
    "愿你眼里有星辰大海",
    "世界很大，慢慢去看",
    "得之坦然，失之淡然",
    "心有山海，静而不争",
    "等风来，不如追风去",
    "花若盛开，蝴蝶自来",
    "积水成渊，积善成德",
    "晚来天欲雪，能饮一杯无",
    "闲看庭前花开花落",
    "宠辱不惊，去留无意",
    "但行好事，莫问前程",
    "心怀热爱，奔赴山海",
    "时间会给你答案",
    "所有的美好，都恰逢其时",
    "愿你成为自己的太阳",
    "细嗅蔷薇，心有猛虎",
    "岁月温柔，人间浪漫",
    "守一颗初心，走漫漫长路",
    "行而不辍，未来可期",
    "心若莲花，一念清净",
    "愿历尽千帆，归来仍少年",
    "低头是题海，抬头是前途",
    "笑看风云淡，坐对云起时",
    "你的善良，自有锋芒",
    "岁月不语，惟石能言",
    "乘风破浪，未来可期",
    "心简单，世界就简单",
    "万水千山总是情",
    "一步一脚印，步步皆从容",
    "心向阳光，温暖向前",
    "愿你既能朝九晚五，又能浪迹天涯",
    "山川是不卷收的文章",
    "保持热爱，奔赴下一场山海",
    "时光不语，静待花开",
    "心中有丘壑，眉目作山河",
    "纵有疾风起，人生不言弃",
    "风雨同舟，温暖前行",
    "予人玫瑰，手有余香",
    "愿你温柔有力量",
    "心若计较少，处处都是晴",
    "一花一世界，一叶一菩提",
    "知进退，明得失",
    "愿岁月可回首，且以深情共白头",
    "心安茅屋稳，性定菜根香",
    "不负韶华，不负己",
    "春和景明，波澜不惊",
    "你笑起来真好看",
    "愿你被这世界温柔以待",
    "岁月静好，现世安稳",
    "心有所信，方能行远",
    "所行皆坦途，所遇皆良人",
    "三餐四季，温暖有趣",
    "愿你成为温暖的人",
    "花香满径，岁月留香",
    "所求皆所愿，所行皆坦途",
]


def _relation(me_wx: str, day_wx: str):
    if me_wx == day_wx:
        return "same"
    if SHENG.get(day_wx) == me_wx:
        return "sheng_me"
    if SHENG.get(me_wx) == day_wx:
        return "me_sheng"
    if KE.get(me_wx) == day_wx:
        return "me_ke"
    if KE.get(day_wx) == me_wx:
        return "ke_me"
    return "same"


def daily_fortune(birth: date, target: date = None, birth_hour: int = None):
    """生成当日运势（纯算法）"""
    target = target or date.today()
    pan = paipan(birth, birth_hour)
    me_wx = pan["day_master_wuxing"]
    day_gz = ganzhi_day(target)
    day_wx_gan = WUXING_GAN[day_gz[0]]
    rel = _relation(me_wx, day_wx_gan)
    level_name, meaning = _FORTUNE_LEVEL[rel]

    # 用日干支序确定性地选宜忌（同一人同一天结果固定）
    seed = (_jdn(target.year, target.month, target.day) + TIANGAN.index(pan["day_master"])) 
    good = [GOOD_POOL[seed % len(GOOD_POOL)], GOOD_POOL[(seed + 3) % len(GOOD_POOL)]]
    avoid = [AVOID_POOL[seed % len(AVOID_POOL)], AVOID_POOL[(seed + 2) % len(AVOID_POOL)]]
    # 吉位/关键词
    keyword_pool = ["稳", "进", "和", "财", "贵", "静", "勤", "信"]
    keyword = keyword_pool[seed % len(keyword_pool)]
    # 今日幸运色：当日五行对应色（缺则补，简化为当日天干五行色）
    lucky = WUXING_COLOR.get(day_wx_gan, WUXING_COLOR["木"])
    quote = DAILY_QUOTES[seed % len(DAILY_QUOTES)]

    return {
        "date": target.isoformat(),
        "day_ganzhi": day_gz,
        "day_wuxing": day_wx_gan,
        "day_master": pan["day_master"],
        "day_master_wuxing": me_wx,
        "relation": level_name,
        "hexagram": f"{day_gz}日 · {level_name}",
        "word": keyword,
        "meaning": meaning,
        "almanac_good": "、".join(dict.fromkeys(good)),
        "almanac_avoid": "、".join(dict.fromkeys(avoid)),
        "liuyue": liuyue(target),
        "liunian": liunian(target),
        "pillars": pan["pillars_text"],
        "shengxiao": pan["shengxiao"],
        "lucky_color": lucky["name"],
        "lucky_color_hex": lucky["hex"],
        "quote": quote,
    }


def monthly_fortune(birth: date, ym: str = None, birth_hour: int = None):
    """月度运势概览"""
    if ym:
        y, m = int(ym[:4]), int(ym[5:7])
    else:
        t = date.today(); y, m = t.year, t.month
    pan = paipan(birth, birth_hour)
    me_wx = pan["day_master_wuxing"]
    mgz = ganzhi_month(y, m)
    rel = _relation(me_wx, WUXING_GAN[mgz[0]])
    level_name, meaning = _FORTUNE_LEVEL[rel]
    return {
        "month": f"{y:04d}-{m:02d}",
        "liuyue": mgz,
        "relation": level_name,
        "summary": f"{y}年{m}月（{mgz}月）：{meaning}",
        "good_events": meaning,
        "caution": _FORTUNE_LEVEL["ke_me"][1] if rel == "ke_me" else "顺势而为，留意月中节奏变化。",
    }


if __name__ == "__main__":
    b = date(1988, 8, 8)
    import json
    print(json.dumps(paipan(b, 10), ensure_ascii=False, indent=2))
    print(json.dumps(daily_fortune(b), ensure_ascii=False, indent=2))
    print(json.dumps(monthly_fortune(b), ensure_ascii=False, indent=2))
