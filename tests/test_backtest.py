"""Phase 2 回测：3 人 × 关键年份方向性正确率 ≥ 70%。

判定逻辑（方向性优先）：
    high = 该年 close 高于 median  或  从上一年上升
    low  = 该年 close 低于 median  或  从上一年下降
    rise = 该年 close > 上一年 close
    fall = 该年 close < 上一年 close
"""
from __future__ import annotations

import pytest

from src.pipeline import pipeline


# (人, 出生参数, [(关键年, 期望方向, 史实标签), ...])
BACKTEST_CASES = [
    ("乔布斯", (1955, 2, 24, 19, 15, "旧金山", 1), [
        (1985, "fall", "被苹果赶出"),
        (1997, "rise", "重返苹果"),
        (2007, "high", "iPhone 发布"),
        (2011, "low",  "去世（软化为低谷）"),
    ]),
    ("马斯克", (1971, 6, 28, 7, 30, "比勒陀利亚", 1), [
        (2002, "high", "PayPal 卖出"),
        (2008, "low",  "Tesla/SpaceX 濒死"),
        (2021, "high", "Tesla 破万亿"),
    ]),
    ("巴菲特", (1930, 8, 30, 15, 0, "奥马哈", 1), [
        (1956, "rise", "创立合伙公司"),
        (1965, "high", "收购伯克希尔"),
        (1999, "low",  "互联网泡沫看空"),
        (2008, "rise", "金融危机抄底"),
    ]),
]


def _check_direction(close_map: dict, year: int, direction: str, median: float) -> bool:
    """方向性判定（宽松：high = 高于中位 或 上升）。"""
    cur = close_map.get(year)
    prev = close_map.get(year - 1)
    if cur is None:
        return False
    if direction == "high":
        return (cur >= median) or (prev is not None and cur > prev)
    if direction == "low":
        return (cur <= median) or (prev is not None and cur < prev)
    if direction == "rise":
        return prev is not None and cur > prev
    if direction == "fall":
        return prev is not None and cur < prev
    raise ValueError(direction)


def _evaluate(args, key_years):
    r = pipeline(*args)
    closes = {k["year"]: k["close"] for k in r["kline"]}
    sc = sorted(closes.values())
    median = sc[len(sc) // 2]
    correct = sum(1 for y, d, _ in key_years if _check_direction(closes, y, d, median))
    return correct, len(key_years), r


# ============================================================
# 单人测试：每人方向性 ≥ 60%（个体可能因纯命理 vs 个人决策而失分）
# ============================================================

@pytest.mark.parametrize("name,args,kys", BACKTEST_CASES, ids=[c[0] for c in BACKTEST_CASES])
def test_per_person_directional_accuracy(name, args, kys):
    correct, total, r = _evaluate(args, kys)
    pct = correct / total
    # 单人 ≥ 60%（容忍 1-2 个由非命理因素主导的关键年错判）
    assert pct >= 0.60, f"{name} 方向性 {correct}/{total} = {pct*100:.0f}% < 60%"


# ============================================================
# 总体测试：合计方向性 ≥ 70%
# ============================================================

def test_overall_directional_accuracy_70pct():
    total_c = total_n = 0
    for name, args, kys in BACKTEST_CASES:
        c, n, _ = _evaluate(args, kys)
        total_c += c
        total_n += n
    pct = total_c / total_n
    assert pct >= 0.70, f"总方向性 {total_c}/{total_n} = {pct*100:.0f}% < 70%"


# ============================================================
# 美化机制：3 人 K 线不能长得一样（区分度检查）
# ============================================================

def test_three_persons_klines_are_distinct():
    """避免美化机制把 3 人都抹平到同一形状。

    检查：两两人 close 序列 Pearson 相关系数 < 0.95（即不完全相同）
    """
    rs = [pipeline(*args) for _, args, _ in BACKTEST_CASES]
    closes = [[k["close"] for k in r["kline"]] for r in rs]

    def pearson(a, b):
        n = min(len(a), len(b))
        ma = sum(a[:n]) / n
        mb = sum(b[:n]) / n
        cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
        sa = (sum((a[i] - ma) ** 2 for i in range(n))) ** 0.5
        sb = (sum((b[i] - mb) ** 2 for i in range(n))) ** 0.5
        if sa == 0 or sb == 0:
            return 1.0
        return cov / (sa * sb)

    for i in range(len(closes)):
        for j in range(i + 1, len(closes)):
            r = pearson(closes[i], closes[j])
            assert r < 0.95, (
                f"{BACKTEST_CASES[i][0]} 与 {BACKTEST_CASES[j][0]} K线相关系数 {r:.3f} "
                f"≥ 0.95，美化机制抹平了个体差异"
            )


# ============================================================
# 美化铁律：3 人都满足 [30,95] + 跌幅 ≤30%
# ============================================================

@pytest.mark.parametrize("name,args,kys", BACKTEST_CASES, ids=[c[0] for c in BACKTEST_CASES])
def test_per_person_kline_constraints(name, args, kys):
    r = pipeline(*args)
    closes = [k["close"] for k in r["kline"]]
    for k in r["kline"]:
        assert 30 <= k["open"] <= 95
        assert 30 <= k["close"] <= 95
        assert 30 <= k["high"] <= 95
        assert 30 <= k["low"] <= 95
        assert k["low"] <= k["open"] <= k["high"]
        assert k["low"] <= k["close"] <= k["high"]
    for i in range(1, len(closes)):
        drop = (closes[i - 1] - closes[i]) / closes[i - 1]
        assert drop <= 0.30 + 0.01, f"{name} idx {i} drop={drop:.3f}"


# ============================================================
# 旺衰判定的合理性
# ============================================================

def test_strength_classifications():
    """三人旺衰应符合传统命理直觉。"""
    # 巴菲特壬水生申月，子日支 = 极强水
    r = pipeline(1930, 8, 30, 15, 0, "奥马哈", 1)
    assert r["chart"]["strength"] == "strong"

    # 乔布斯丙火生寅月（长生），日支辰晦火但月令旺 → strong
    r = pipeline(1955, 2, 24, 19, 15, "旧金山", 1)
    assert r["chart"]["strength"] == "strong"

    # 1991 壬水生巳月（绝），无金生 → balanced 偏弱
    r = pipeline(1991, 5, 12, 8, 0, "北京", 1)
    assert r["chart"]["strength"] in ("balanced", "weak")
