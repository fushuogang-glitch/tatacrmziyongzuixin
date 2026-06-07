"""塔才评语引擎 — 内置算法版（A方案先用，保留塔才真AI接口B方案）
输入：四色性格 + MBTI + 八字命理 → 输出：性格评语 / 沟通注意事项 / 经营销售提醒 / 服务接待建议
"""
import re

# 四色性格特征
COLOR_TRAITS = {
    "红": {"key": "红色力量型", "traits": "目标导向、果断直接、节奏快、重结果",
          "comm": "说话直奔主题、给选择题不要开放题、尊重其主导权、别拖泥带水",
          "biz": "用'稀缺/限时/效果'促单，给方案要快准狠，敢于逼单",
          "serv": "服务高效、不啰嗦、让其感到被重视和掌控"},
    "黄": {"key": "黄色活泼型", "traits": "热情外向、爱社交、重感受、易冲动",
          "comm": "多互动多夸赞、营造氛围、聊兴趣聊生活、给情绪价值",
          "biz": "用'体验/新品/朋友圈'吸引，制造惊喜感，借社交裂变",
          "serv": "服务有仪式感、多互动、记住其喜好、给惊喜"},
    "蓝": {"key": "蓝色理性型", "traits": "严谨细致、重逻辑、谨慎、要数据",
          "comm": "给数据给原理给案例、有耐心、不夸大、让其自己判断",
          "biz": "用'专业/成分/对比/口碑'说服，提供详细方案书，给思考空间",
          "serv": "服务规范专业、流程透明、术前术后讲清楚、不催"},
    "绿": {"key": "绿色平和型", "traits": "随和稳定、重关系、怕冲突、决策慢",
          "comm": "温和耐心、多陪伴、不施压、建立长期信任",
          "biz": "用'陪伴/老客优惠/无压力'软推，慢慢培育，靠关系成交",
          "serv": "服务温馨稳定、固定专属顾问、让其有安全感"},
}

# MBTI 维度补充
MBTI_HINT = {
    "E": "外向，沟通可多互动", "I": "内向，给独处和思考空间",
    "T": "理性决策，讲逻辑和事实", "F": "感性决策，重情感共鸣",
    "J": "计划性强，给清晰安排", "P": "灵活随性，留弹性空间",
    "S": "务实，讲具体细节", "N": "重愿景，讲长远价值",
}


def _parse_color(color_str: str) -> str:
    """从'金色行动型/红色'等文本提取主色"""
    if not color_str:
        return ""
    for c in ["红", "黄", "蓝", "绿"]:
        if c in color_str:
            return c
    # 金色≈红，银/白≈蓝 等近似
    if "金" in color_str or "橙" in color_str:
        return "红"
    if "粉" in color_str:
        return "黄"
    return ""


def _mbti_hints(mbti: str) -> str:
    if not mbti:
        return ""
    mbti = mbti.upper().strip()
    m = re.search(r"[EI][NS][TF][JP]", mbti)
    if not m:
        return ""
    code = m.group(0)
    return "；".join(MBTI_HINT[c] for c in code if c in MBTI_HINT)


def generate(color_personality: str = None, mbti: str = None,
             bazi_analysis: str = None, name: str = "该客户") -> dict:
    """生成塔才四块评语"""
    color = _parse_color(color_personality or "")
    ct = COLOR_TRAITS.get(color)
    mbti_hint = _mbti_hints(mbti or "")

    # 性格评语
    if ct:
        comment = f"{name}属于「{ct['key']}」，{ct['traits']}。"
    else:
        comment = f"{name}的性格画像待补充四色性格后更精准。"
    if mbti:
        comment += f"MBTI 为 {mbti.upper().strip()}。"
    if mbti_hint:
        comment += f"（{mbti_hint}）"
    if bazi_analysis:
        comment += f"\n命理参考：{bazi_analysis[:120]}"

    # 沟通注意事项
    communication = ct["comm"] if ct else "建议先补充四色性格，再生成精准沟通策略。"
    if mbti_hint:
        communication += f"。结合 MBTI：{mbti_hint}"

    # 经营销售提醒
    business = ct["biz"] if ct else "成交策略待四色性格补充后生成。"

    # 服务接待建议
    service = ct["serv"] if ct else "服务建议待四色性格补充后生成。"

    return {
        "comment": comment,
        "communication": communication,
        "business_tip": business,
        "service_tip": service,
        "engine": "builtin",  # builtin=内置算法 / taicai=真塔才AI
    }


if __name__ == "__main__":
    import json
    print(json.dumps(generate("金色行动型/红色", "ENTJ", "日主甲木，财星旺", "薛女士"),
                     ensure_ascii=False, indent=2))
