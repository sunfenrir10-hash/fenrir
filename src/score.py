"""三层评分模块：大运 (±100) + 流年 (±30) + 流月 (±20)。

V1 简化：
- 不做日主旺衰判断；统一按"十神本义"打分。
- 地支权重 = 天干权重 × 0.5。
- 所有权重集中在模块顶部常量，方便 Phase 2 调参。

评分公式（每一层对日主的影响）：
    layer_score = Σ gan_contrib_i + Σ zhi_contrib_j + Σ zhi_relation_k

    gan_contrib(gan_X, day_master) = TG_WEIGHT[十神关系]
    zhi_contrib(zhi_X, day_master) = TG_WEIGHT[十神关系] × 0.5
    zhi_relation(zhi_X, natal_zhi) = DZ_MOD[关系类型]  # 六合/三合/冲/害/刑/三会
"""
from __future__ import annotations

from typing import Iterable

from .bazi import GAN_TO_ELEMENT, ZHI_TO_ELEMENT, GAN_YINYANG

# ========================================================================
# 权重表（Phase 2 调参入口）
# ========================================================================

#: 天干十神关系权重（对日主的影响）
TG_WEIGHT: dict[str, float] = {
    "比劫": +10,   # 同我：帮扶
    "印":   +15,   # 生我：贵人/资源
    "食伤":  -5,   # 我生：泄耗
    "财":   +20,   # 我克：财富机会
    "官杀": -15,   # 克我：压力/阻碍
}

#: 地支权重系数（地支力量 = 天干 × 此系数）
ZHI_WEIGHT_RATIO: float = 0.5

#: 地支关系修正
DZ_MOD: dict[str, float] = {
    "六合":  +10,
    "三合":  +15,
    "三会":  +20,
    "六冲":  -20,
    "六害":  -10,
    "三刑":  -15,
}

#: 各层打分的最终 clip 范围
DAYUN_CLIP = (-100.0, 100.0)
LIUNIAN_CLIP = (-30.0, 30.0)
LIUYUE_CLIP = (-20.0, 20.0)

# ========================================================================
# 五行 × 十神关系表
# ========================================================================

#: 五行相生: A -> A 生的
ELEMENT_GENERATES: dict[str, str] = {
    "木": "火", "火": "土", "土": "金", "金": "水", "水": "木",
}
#: 五行相克: A -> A 克的
ELEMENT_CONTROLS: dict[str, str] = {
    "木": "土", "土": "水", "水": "火", "火": "金", "金": "木",
}


def ten_god_relation(other_element: str, day_master_element: str,
                     other_yinyang: str | None = None,
                     day_master_yinyang: str | None = None) -> str:
    """返回 other 对日主的十神大类关系。

    V1 只区分 5 大类（不细分正印/偏印、正官/七杀等）：
        比劫 / 印 / 食伤 / 财 / 官杀
    """
    dm = day_master_element
    o = other_element
    if o == dm:
        return "比劫"
    if ELEMENT_GENERATES.get(o) == dm:  # 生我
        return "印"
    if ELEMENT_GENERATES.get(dm) == o:  # 我生
        return "食伤"
    if ELEMENT_CONTROLS.get(dm) == o:   # 我克
        return "财"
    if ELEMENT_CONTROLS.get(o) == dm:   # 克我
        return "官杀"
    # 理论上不可达
    raise ValueError(f"无法判定 {o} 相对 {dm} 的十神关系")


# ========================================================================
# 地支关系集合
# ========================================================================

#: 六合：6 组
LIU_HE: set[frozenset[str]] = {
    frozenset({"子", "丑"}), frozenset({"寅", "亥"}),
    frozenset({"卯", "戌"}), frozenset({"辰", "酉"}),
    frozenset({"巳", "申"}), frozenset({"午", "未"}),
}

#: 六冲：6 组
LIU_CHONG: set[frozenset[str]] = {
    frozenset({"子", "午"}), frozenset({"丑", "未"}),
    frozenset({"寅", "申"}), frozenset({"卯", "酉"}),
    frozenset({"辰", "戌"}), frozenset({"巳", "亥"}),
}

#: 六害：6 组
LIU_HAI: set[frozenset[str]] = {
    frozenset({"子", "未"}), frozenset({"丑", "午"}),
    frozenset({"寅", "巳"}), frozenset({"卯", "辰"}),
    frozenset({"申", "亥"}), frozenset({"酉", "戌"}),
}

#: 三合局：4 组（每组 3 个地支齐才算全三合；V1 里只要有 2 个就算半合加分）
SAN_HE_TRIPLES: list[frozenset[str]] = [
    frozenset({"申", "子", "辰"}),  # 水局
    frozenset({"亥", "卯", "未"}),  # 木局
    frozenset({"寅", "午", "戌"}),  # 火局
    frozenset({"巳", "酉", "丑"}),  # 金局
]

#: 三会：4 组（东方木/南方火/西方金/北方水）
SAN_HUI_TRIPLES: list[frozenset[str]] = [
    frozenset({"寅", "卯", "辰"}),  # 东方木
    frozenset({"巳", "午", "未"}),  # 南方火
    frozenset({"申", "酉", "戌"}),  # 西方金
    frozenset({"亥", "子", "丑"}),  # 北方水
]

#: 三刑：传统"子卯相刑"、"寅巳申三刑"、"丑戌未三刑"、自刑（辰辰/午午/酉酉/亥亥）
SAN_XING_PAIRS: set[frozenset[str]] = {
    # 无礼之刑
    frozenset({"子", "卯"}),
}
SAN_XING_TRIPLES: list[frozenset[str]] = [
    frozenset({"寅", "巳", "申"}),  # 无恩之刑
    frozenset({"丑", "戌", "未"}),  # 恃势之刑
]
#: 自刑（同支对同支）
SELF_XING: set[str] = {"辰", "午", "酉", "亥"}


# ========================================================================
# 地支关系判定
# ========================================================================

def _zhi_pair_relation(z1: str, z2: str) -> list[str]:
    """返回两个地支的关系列表（可能多个：如同时六合又……）。

    只判定二元关系：六合/六冲/六害；
    三合/三会/三刑以 pair 方式检测（任意两支都在同一 triple 中计 +0.5 倍分）。
    """
    rels: list[str] = []
    pair = frozenset({z1, z2})
    if pair in LIU_HE:
        rels.append("六合")
    if pair in LIU_CHONG:
        rels.append("六冲")
    if pair in LIU_HAI:
        rels.append("六害")
    if pair in SAN_XING_PAIRS:
        rels.append("三刑")
    # 自刑（同支）
    if z1 == z2 and z1 in SELF_XING:
        rels.append("三刑")
    return rels


def _check_group_relation(target_zhi: str, natal_zhi_list: Iterable[str],
                          triples: list[frozenset[str]],
                          *, require_full: bool = True) -> bool:
    """检测 target_zhi 是否与 natal 的地支一起凑齐某个 triple。

    require_full=True：要求 target + natal 合起来包含 triple 全部 3 个地支
                      （target 必须是其中之一，natal 必须贡献另外 2 个）
    require_full=False：只要 target 在 triple 中且 natal 至少贡献 1 个（半合），就算
    """
    natal_set = set(natal_zhi_list)
    for triple in triples:
        if target_zhi not in triple:
            continue
        others = triple - {target_zhi}
        natal_hit = sum(1 for z in others if z in natal_set)
        if require_full:
            if natal_hit >= 2:  # target + 2 natal = 全部 3 支
                return True
        else:
            if natal_hit >= 1:
                return True
    return False


def evaluate_zhi_relations(target_zhi: str, natal_zhi_list: Iterable[str]) -> float:
    """计算 target_zhi 相对命局 natal 地支的关系得分。

    - 对 natal 每个地支做二元判定（六合/冲/害/子卯刑/自刑）
    - 整体判定三合/三会/寅巳申/丑戌未三刑
    返回总分。
    """
    natal = list(natal_zhi_list)
    total = 0.0

    # 二元关系
    for nz in natal:
        for rel in _zhi_pair_relation(target_zhi, nz):
            total += DZ_MOD[rel]

    # 三合（含半合：target + 1 natal 也算，但分数减半）
    if _check_group_relation(target_zhi, natal, SAN_HE_TRIPLES, require_full=True):
        total += DZ_MOD["三合"]
    elif _check_group_relation(target_zhi, natal, SAN_HE_TRIPLES, require_full=False):
        total += DZ_MOD["三合"] * 0.5  # 半合
    # 三会（必须全 3 支齐）
    if _check_group_relation(target_zhi, natal, SAN_HUI_TRIPLES, require_full=True):
        total += DZ_MOD["三会"]
    # 三刑（多元，必须 triple 全齐）
    if _check_group_relation(target_zhi, natal, SAN_XING_TRIPLES, require_full=True):
        total += DZ_MOD["三刑"]

    return total


# ========================================================================
# 单柱对日主的评分（干 + 支本身对日主的十神关系分；不含地支关系修正）
# ========================================================================

def _pillar_self_score(gan: str, zhi: str, day_master_element: str,
                       favor: dict[str, float] | None = None) -> float:
    """一柱（干 + 支）本身对日主的十神得分。

    干/支 各自按五行计算十神关系：
        干分 = TG_WEIGHT[十神(干)] × favor[十神(干)]
        支分 = TG_WEIGHT[十神(支)] × favor[十神(支)] × ZHI_WEIGHT_RATIO

    favor: 喜用神倍率（来自 strength.favor_multipliers）。None 时全部 = 1.0（等价于平衡）。
    """
    gan_el = GAN_TO_ELEMENT[gan]
    zhi_el = ZHI_TO_ELEMENT[zhi]
    gan_rel = ten_god_relation(gan_el, day_master_element)
    zhi_rel = ten_god_relation(zhi_el, day_master_element)
    if favor is None:
        gm = zm = 1.0
    else:
        gm = favor.get(gan_rel, 1.0)
        zm = favor.get(zhi_rel, 1.0)
    return TG_WEIGHT[gan_rel] * gm + TG_WEIGHT[zhi_rel] * zm * ZHI_WEIGHT_RATIO


def _clip(x: float, bounds: tuple[float, float]) -> float:
    lo, hi = bounds
    return max(lo, min(hi, x))


# ========================================================================
# 三层评分函数
# ========================================================================

def score_dayun(dayun_ganzhi: str, day_master_element: str,
                natal_zhi_list: list[str],
                favor: dict[str, float] | None = None) -> float:
    """大运基础分 [±100]。

    = 大运干对日主的分 + 大运支对日主的分 + 大运支与命局地支的关系分 × 放大系数
    favor: 喜用神倍率（来自 strength.favor_multipliers）
    """
    if not dayun_ganzhi or len(dayun_ganzhi) < 2:
        return 0.0
    gan, zhi = dayun_ganzhi[0], dayun_ganzhi[1]
    base = _pillar_self_score(gan, zhi, day_master_element, favor=favor)
    # 大运权重：基础分 × 1.5（Phase 2 调整：原为 ×2，避免 10 年走势同质化）
    base *= 1.5
    rel = evaluate_zhi_relations(zhi, natal_zhi_list)
    total = base + rel
    return _clip(total, DAYUN_CLIP)


def score_liunian(liunian_gz: str, dayun_gz: str, day_master_element: str,
                  natal_zhi_list: list[str],
                  favor: dict[str, float] | None = None) -> float:
    """流年修正分 [±30]。"""
    if not liunian_gz or len(liunian_gz) < 2:
        return 0.0
    gan, zhi = liunian_gz[0], liunian_gz[1]
    base = _pillar_self_score(gan, zhi, day_master_element, favor=favor)
    rel_targets = list(natal_zhi_list)
    if dayun_gz and len(dayun_gz) >= 2:
        rel_targets.append(dayun_gz[1])
    rel = evaluate_zhi_relations(zhi, rel_targets)
    total = (base + rel) * 0.5
    return _clip(total, LIUNIAN_CLIP)


def score_liuyue(yue_gz: str, liunian_gz: str, day_master_element: str,
                 favor: dict[str, float] | None = None) -> float:
    """流月波动分 [±20]。"""
    if not yue_gz or len(yue_gz) < 2:
        return 0.0
    gan, zhi = yue_gz[0], yue_gz[1]
    base = _pillar_self_score(gan, zhi, day_master_element, favor=favor)

    rel = 0.0
    if liunian_gz and len(liunian_gz) >= 2:
        ln_zhi = liunian_gz[1]
        for r in _zhi_pair_relation(zhi, ln_zhi):
            rel += DZ_MOD[r]
    total = (base + rel) * 0.4
    return _clip(total, LIUYUE_CLIP)


# ========================================================================
# 聚合：年度 12 月分数
# ========================================================================

def compute_year_score(year: int, chart, *, return_breakdown: bool = False,
                       favor: dict[str, float] | None = None) -> dict:
    """计算某公历年份的 12 个月原始分数。

    favor 由 strength.favor_multipliers(strength) 得到；如果不传，调用方负责或退化为平衡。
    """
    from .bazi import get_dayun_for_year  # 延迟引入避免循环

    dayun = get_dayun_for_year(chart, year)
    dayun_gz = dayun.ganzhi if dayun else ""
    dayun_sc = score_dayun(dayun_gz, chart.day_master_element, chart.natal_zhi_list,
                           favor=favor)

    liunian_gz = chart.liunian_map.get(year, "")
    liunian_sc = score_liunian(liunian_gz, dayun_gz, chart.day_master_element,
                               chart.natal_zhi_list, favor=favor)

    months = chart.liuyue_map.get(year, [])
    monthly: list[float] = []
    yue_breakdown: list[dict] = []
    for m_int, yue_gz in months:
        yue_sc = score_liuyue(yue_gz, liunian_gz, chart.day_master_element, favor=favor)
        total = dayun_sc + liunian_sc + yue_sc
        monthly.append(total)
        if return_breakdown:
            yue_breakdown.append({
                "month": m_int, "gz": yue_gz, "yue_score": yue_sc, "total": total,
            })

    age = year - chart.solar_birth.year + 1

    out = {
        "year": year,
        "age": age,
        "dayun_gz": dayun_gz,
        "dayun_score": dayun_sc,
        "liunian_gz": liunian_gz,
        "liunian_score": liunian_sc,
        "monthly_scores": monthly,
    }
    if return_breakdown:
        out["breakdown"] = {"months": yue_breakdown}
    return out


def compute_century_scores(chart, horizon_years: int = 100,
                           favor: dict[str, float] | None = None) -> list[dict]:
    """计算 100 年每年的月度分数列表。"""
    results: list[dict] = []
    start_year = chart.solar_birth.year
    for i in range(horizon_years):
        y = start_year + i
        results.append(compute_year_score(y, chart, favor=favor))
    return results
