"""日主旺衰判断（V1.5 简化版）。

核心思路：用四个常见信号给日主打"力量分"，分三档输出：
    -  身旺（strong）：日主有力，喜财官食伤来泄/克
    -  平衡（balanced）：维持基础权重表
    -  身弱（weak）：日主无力，喜印比来生/扶

V1.5 不做的事（V2 再细化）：
    - 不算调候用神（夏火忌火、冬水忌水等）
    - 不区分正偏印、正偏官等
    - 不做八字格局分析（建禄/伤官生财等）

四个信号（共 +12 ~ -12 力量分）：
    1. 月令得气（±5）
       - 长生/帝旺/临官/冠带 → +5（最关键，月令是旺衰的核心）
       - 沐浴/衰/病 → 0（中性）
       - 死/墓/绝/胎/养 → -5
    2. 日支根气（±3）
       - 日支藏干含日干同五行 → +3（坐根）
       - 日支为日干所克（财） → -2
    3. 透干帮扶（±3，最多 +3）
       - 年/月/时干含与日干同五行 → 每个 +1.5
       - 年/月/时干含生日干五行（印） → 每个 +1
    4. 地支帮扶（±2，最多 +2）
       - 年/月/时支藏干含与日干或印同五行 → 每个 +0.5

综合分:
    >= +4 → strong
    -3 ~ +3 → balanced
    <= -4 → weak
"""
from __future__ import annotations

from typing import Literal

from .bazi import GAN_TO_ELEMENT, ZHI_TO_ELEMENT, BaziChart

Strength = Literal["strong", "balanced", "weak"]


# 十二长生表：日干 -> {地支: 长生状态}
# 状态权重：长生/帝旺/临官/冠带 = +5；沐浴/衰/病 = 0；死/墓/绝/胎/养 = -5
# 数据来自传统命理"五行十二长生"（阳干顺行、阴干逆行）
# 简化：阳干和阴干用同一表（V2 可分阴阳精修）
_TWELVE_STAGES: dict[str, dict[str, str]] = {
    # 木日干（甲乙）
    "木": {
        "亥": "长生", "子": "沐浴", "丑": "冠带", "寅": "临官",
        "卯": "帝旺", "辰": "衰",   "巳": "病",   "午": "死",
        "未": "墓",   "申": "绝",   "酉": "胎",   "戌": "养",
    },
    # 火日干（丙丁）
    "火": {
        "寅": "长生", "卯": "沐浴", "辰": "冠带", "巳": "临官",
        "午": "帝旺", "未": "衰",   "申": "病",   "酉": "死",
        "戌": "墓",   "亥": "绝",   "子": "胎",   "丑": "养",
    },
    # 土日干（戊己）—— 传统寄火，与火同
    "土": {
        "寅": "长生", "卯": "沐浴", "辰": "冠带", "巳": "临官",
        "午": "帝旺", "未": "衰",   "申": "病",   "酉": "死",
        "戌": "墓",   "亥": "绝",   "子": "胎",   "丑": "养",
    },
    # 金日干（庚辛）
    "金": {
        "巳": "长生", "午": "沐浴", "未": "冠带", "申": "临官",
        "酉": "帝旺", "戌": "衰",   "亥": "病",   "子": "死",
        "丑": "墓",   "寅": "绝",   "卯": "胎",   "辰": "养",
    },
    # 水日干（壬癸）
    "水": {
        "申": "长生", "酉": "沐浴", "戌": "冠带", "亥": "临官",
        "子": "帝旺", "丑": "衰",   "寅": "病",   "卯": "死",
        "辰": "墓",   "巳": "绝",   "午": "胎",   "未": "养",
    },
}

_STAGE_SCORE: dict[str, float] = {
    "长生": +5, "临官": +5, "帝旺": +5, "冠带": +4,
    "沐浴": 0,  "衰": 0,    "病": 0,
    "死": -5,   "墓": -3,   "绝": -5,   "胎": -3, "养": -2,
}


# 地支藏干（主气 + 余气 + 杂气，简化只取主气和明显的余气）
# 数据来自传统命理"地支藏干表"
_DIZHI_HIDDEN: dict[str, list[str]] = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "戊", "庚"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}


# 五行相生：A 生 B  ↔  生我者为印
_GENERATES: dict[str, str] = {
    "木": "火", "火": "土", "土": "金", "金": "水", "水": "木",
}


def _yin_element(element: str) -> str:
    """返回生此五行的元素（印星五行）。"""
    for src, dst in _GENERATES.items():
        if dst == element:
            return src
    raise ValueError(element)


def compute_strength_score(chart: BaziChart) -> float:
    """计算日主力量原始分（约在 -12 ~ +12 之间）。"""
    dm_el = chart.day_master_element
    yin_el = _yin_element(dm_el)  # 生我者（印星）

    score = 0.0

    # 1. 月令得气（最关键）
    month_zhi = chart.month_pillar.zhi
    stage = _TWELVE_STAGES[dm_el].get(month_zhi)
    if stage is not None:
        score += _STAGE_SCORE.get(stage, 0)

    # 2. 日支根气
    day_zhi = chart.day_pillar.zhi
    day_zhi_hidden_elements = [GAN_TO_ELEMENT[g] for g in _DIZHI_HIDDEN.get(day_zhi, [])]
    if dm_el in day_zhi_hidden_elements:
        score += 3
    elif _GENERATES.get(dm_el) in day_zhi_hidden_elements:
        # 日支为日主所生（食伤）—— 略泄
        score -= 1

    # 3. 透干帮扶（年/月/时干，不含日干本身）
    other_gans = [chart.year_pillar.gan, chart.month_pillar.gan, chart.hour_pillar.gan]
    transparent_help = 0.0
    for g in other_gans:
        g_el = GAN_TO_ELEMENT[g]
        if g_el == dm_el:
            transparent_help += 1.5      # 比劫透干
        elif g_el == yin_el:
            transparent_help += 1.0      # 印透干
    score += min(transparent_help, 3.0)

    # 4. 地支帮扶（年/月/时支，不含日支重复计算月令）
    # 月支已在 #1 计入，所以这里只看年支和时支
    other_zhis = [chart.year_pillar.zhi, chart.hour_pillar.zhi]
    branch_help = 0.0
    for z in other_zhis:
        hidden = [GAN_TO_ELEMENT[g] for g in _DIZHI_HIDDEN.get(z, [])]
        if dm_el in hidden:
            branch_help += 0.5
        if yin_el in hidden:
            branch_help += 0.5
    score += min(branch_help, 2.0)

    return score


def classify_strength(chart: BaziChart) -> tuple[Strength, float]:
    """判定日主旺衰档位。"""
    raw = compute_strength_score(chart)
    if raw >= 4:
        return ("strong", raw)
    elif raw <= -4:
        return ("weak", raw)
    else:
        return ("balanced", raw)


# ============================================================
# 喜用神：根据旺衰返回每个十神类的"喜用倍率"
# ============================================================

def favor_multipliers(strength: Strength) -> dict[str, float]:
    """返回十神 → 倍率（应用到 TG_WEIGHT 上）。

    逻辑（粗粒度）：
      - 身旺（强）：忌印比（生扶过多），喜财官食伤（克泄）
        → 比劫 × 0.4（接近抹平 +10），印 × 0.4
        → 财 × 1.0（保持 +20，对身旺人是真财）
        → 官杀 × 0.7（依然是压力但伤害减小，因身强能担官）
        → 食伤 × 1.6（×-5 → -8，因身旺需泄秀，食伤反而是好事 → 翻号反向不科学，
                      改为 ×-1.5 表示泄秀有益 = +7.5 见下方逻辑）
      - 身弱（弱）：喜印比（生扶），忌财官食伤
        → 比劫 × 1.4，印 × 1.4
        → 财 × -1.0（财耗身，反向）
        → 官杀 × 1.5（官杀克身更凶）
        → 食伤 × 1.8（食伤盗气更耗）
      - 平衡：全部 × 1.0

    返回 dict: { "比劫": 倍率, "印": 倍率, "食伤": 倍率, "财": 倍率, "官杀": 倍率,
                 "_食伤_反号": True/False, "_财_反号": True/False }

    "反号"标记：原 TG_WEIGHT 中食伤=-5、官杀=-15 是负的；
    对身旺人，食伤"泄秀"应为正 → 反号；
    对身弱人，财"耗身"原本是正（+20），应反号为负。
    """
    if strength == "strong":
        # 身旺：喜财、喜食伤泄秀、喜官杀（克身正合）；忌印比生扶过度
        # V1.5 经验调整：经回测，官杀对身旺人应为中性偏正（担官 = 富贵），
        # 但避免过度正向导致去世年误判，设为 0（中性）
        return {
            "比劫": -0.3,    # 反号：原 +10 × -0.3 = -3
            "印":   -0.2,    # 反号：原 +15 × -0.2 = -3
            "食伤": -1.4,    # 反号：原 -5 × -1.4 = +7（泄秀）
            "财":   1.2,    # 原 +20 × 1.2 = +24
            "官杀": 0.0,    # 中性：身旺担官，但难以仅凭五行判富贵/灾祸
        }
    elif strength == "weak":
        # 身弱：喜印比，忌财官食伤
        return {
            "比劫": 1.6,    # 原 +10 × 1.6 = +16
            "印":   1.6,    # 原 +15 × 1.6 = +24
            "食伤": 1.8,    # 原 -5 × 1.8 = -9
            "财":   -1.0,   # 反号：原 +20 × -1.0 = -20
            "官杀": 1.5,    # 原 -15 × 1.5 = -22.5
        }
    else:  # balanced
        return {"比劫": 1.0, "印": 1.0, "食伤": 1.0, "财": 1.0, "官杀": 1.0}
