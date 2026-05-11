"""端到端测试：排盘 -> 评分 -> 美化 -> K 线。"""
from __future__ import annotations

import pytest

from src.pipeline import pipeline
from src.bazi import compute_bazi
from src.score import (
    ten_god_relation,
    evaluate_zhi_relations,
    score_dayun, score_liunian, score_liuyue,
)
from src.sanitize import (
    sanitize, sanitize_monthly_matrix, apply_elder_soften,
    DISPLAY_MIN, DISPLAY_MAX,
)


# ============================================================
# Pipeline 端到端
# ============================================================

def test_pipeline_1991_beijing_male():
    """(1991-05-12 08:00 北京 男) 跑 100 根 K 线。"""
    result = pipeline(1991, 5, 12, 8, 0, "北京", gender=1)
    kline = result["kline"]
    assert len(kline) == 100

    for c in kline:
        # 基本字段
        for k in ("open", "high", "low", "close", "volume", "year", "age", "color"):
            assert k in c
        # 展示分区间
        assert DISPLAY_MIN <= c["open"] <= DISPLAY_MAX
        assert DISPLAY_MIN <= c["close"] <= DISPLAY_MAX
        assert DISPLAY_MIN <= c["high"] <= DISPLAY_MAX
        assert DISPLAY_MIN <= c["low"] <= DISPLAY_MAX
        # OHLC 内部一致性
        assert c["low"] <= c["open"] <= c["high"]
        assert c["low"] <= c["close"] <= c["high"]


def test_yearly_close_drop_capped_at_30pct():
    """任意相邻年 close 跌幅 ≤ 30%（允许 K 线 2 位小数舍入误差）。"""
    result = pipeline(1991, 5, 12, 8, 0, "北京", gender=1)
    closes = [c["close"] for c in result["kline"]]
    for i in range(1, len(closes)):
        drop = (closes[i - 1] - closes[i]) / closes[i - 1]
        # 0.01 缓冲是为容忍 build_kline 的 round(x, 2) 舍入
        assert drop <= 0.30 + 0.01, (
            f"Year idx {i}: drop={drop:.4f} from {closes[i-1]:.2f} to {closes[i]:.2f}"
        )


def test_four_pillars_1991_beijing():
    """对照卜易居等：1991-05-12 08:00 北京男 四柱应为 辛未/癸巳/壬午/甲辰。

    注：08:00 经真太阳时修正后 ≈ 08:00 - 14min ≈ 07:46，仍在辰时，故时柱 = 甲辰。
    """
    r = pipeline(1991, 5, 12, 8, 0, "北京", gender=1)
    fp = r["chart"]["four_pillars"]
    assert fp["year"] == "辛未"
    assert fp["month"] == "癸巳"
    assert fp["day"] == "壬午"
    assert fp["hour"] == "甲辰"
    assert r["chart"]["day_master"] == "壬水"


# ============================================================
# score 单元测试
# ============================================================

def test_ten_god_relation_basics():
    # 日主壬水，甲木是食伤（我生）
    assert ten_god_relation("木", "水") == "食伤"
    # 日主壬水，金是印（生我）
    assert ten_god_relation("金", "水") == "印"
    # 日主壬水，火是财（我克）
    assert ten_god_relation("火", "水") == "财"
    # 日主壬水，土是官杀（克我）
    assert ten_god_relation("土", "水") == "官杀"
    # 比劫
    assert ten_god_relation("水", "水") == "比劫"


def test_zhi_six_he():
    # 子丑六合
    score = evaluate_zhi_relations("子", ["丑"])
    assert score == 10  # 六合 +10


def test_zhi_six_chong():
    # 子午六冲
    score = evaluate_zhi_relations("子", ["午"])
    assert score == -20  # -20


def test_zhi_san_he():
    """三合：申子辰全齐（子 + natal 含申+辰）= +15。"""
    score = evaluate_zhi_relations("子", ["申", "辰"])
    # 全三合 +15；子 也不与 申/辰 构成 二元六合/冲/害
    assert score == pytest.approx(15.0)


def test_zhi_half_san_he():
    """半合：申子（缺辰）= +7.5。"""
    score = evaluate_zhi_relations("子", ["申"])
    assert score == pytest.approx(7.5)


def test_score_dayun_ranges():
    # 任意大运干支对任意日主，都应在 [-100, 100] 内
    for gz in ["甲子", "丙午", "庚申", "壬辰", "戊戌"]:
        for dm in ["木", "火", "土", "金", "水"]:
            s = score_dayun(gz, dm, ["子", "午", "卯", "酉"])
            assert -100 <= s <= 100


def test_score_liunian_ranges():
    for gz in ["甲子", "辛未", "癸亥"]:
        for dm in ["木", "火", "土", "金", "水"]:
            s = score_liunian(gz, "甲寅", dm, ["子", "午"])
            assert -30 <= s <= 30


def test_score_liuyue_ranges():
    for gz in ["丙寅", "丁卯", "戊辰"]:
        for dm in ["木", "火", "土", "金", "水"]:
            s = score_liuyue(gz, "辛未", dm)
            assert -20 <= s <= 20


# ============================================================
# sanitize 单元测试
# ============================================================

def test_sanitize_range():
    raw = [-100, -50, 0, 50, 100]
    out = sanitize(raw)
    for v in out:
        assert DISPLAY_MIN <= v <= DISPLAY_MAX


def test_sanitize_drop_cap():
    # 从 95 骤降到 -100 应被限制在 95 × 0.7 = 66.5
    raw = [100, -100]
    out = sanitize(raw)
    assert out[0] == pytest.approx(95.0)
    assert out[1] >= 95.0 * 0.7 - 1e-6


def test_sanitize_matrix_preserves_12_months():
    matrix = [[i + m for m in range(12)] for i in range(-50, 50)]  # 100 year
    out = sanitize_monthly_matrix(matrix)
    assert len(out) == 100
    for y in out:
        assert len(y) == 12
        for v in y:
            assert DISPLAY_MIN <= v <= DISPLAY_MAX


# ============================================================
# 历史命盘交叉校验（只校验四柱，不校验大运走势）
# ============================================================

def test_jobs_1955_san_francisco():
    """乔布斯 1955-02-24 19:15 旧金山男。

    参考（bazi8.net 案例）：
      年柱=乙未  月柱=戊寅  日柱=丙辰  时柱=丁酉
    V1 未加 EoT（均时差），时柱可能落在 丁酉 / 戊戌 之间，放宽断言。
    """
    r = pipeline(1955, 2, 24, 19, 15, "旧金山", gender=1)
    fp = r["chart"]["four_pillars"]
    assert fp["year"] == "乙未"
    assert fp["month"] == "戊寅"
    assert fp["day"] == "丙辰"
    assert fp["hour"] in ("丁酉", "戊戌")


def test_musk_1971_pretoria():
    """马斯克 1971-06-28 07:30 比勒陀利亚男。

    公开资料（多家命理站一致）：
      年=辛亥  月=甲午  日=甲申  时=戊辰
    """
    r = pipeline(1971, 6, 28, 7, 30, "比勒陀利亚", gender=1)
    fp = r["chart"]["four_pillars"]
    assert fp["year"] == "辛亥"
    assert fp["month"] == "甲午"
    assert fp["day"] == "甲申"
    assert fp["hour"] == "戊辰"


# ============================================================
# 老人软化（Phase 3）
# ============================================================

def test_elder_soften_pushes_min_below_threshold():
    """age > 70 段月最低分应被下压（默认 6 分），未到年龄段不动。"""
    # 构造 5 年矩阵，每年 12 个月分都 = 70
    matrix = [[70.0] * 12 for _ in range(5)]
    ages = [69, 70, 71, 75, 80]
    out = apply_elder_soften(matrix, ages, threshold=70, push_down=6.0)
    assert min(out[0]) == 70.0    # age 69 不动
    assert min(out[1]) == 70.0    # age 70 不动 (> threshold 才生效)
    assert min(out[2]) == 64.0    # age 71 下压 6
    assert min(out[3]) == 64.0
    assert min(out[4]) == 64.0
    # 其余月份不变
    assert sum(1 for v in out[2] if v == 70.0) == 11


def test_elder_soften_floor_at_30():
    """下压不得突破 DISPLAY_MIN=30。"""
    matrix = [[33.0] * 12]
    out = apply_elder_soften(matrix, ages=[80], threshold=70, push_down=10.0)
    assert min(out[0]) == DISPLAY_MIN  # 33 - 10 = 23 → clip 到 30


def test_elder_soften_buffett_2010_2020_segment():
    """巴菲特（1930 生）2010-2020 段月最低值应被下压（age 80-90）。"""
    r = pipeline(1930, 8, 30, 15, 0, "奥马哈", 1)
    # 取 2010-2020 段
    elder_lows = [k["low"] for k in r["kline"] if 2010 <= k["year"] <= 2020]
    assert len(elder_lows) == 11
    # 平均 low 应明显低于"未软化"基线（≤72，否则证明老人软化没生效）
    avg_low = sum(elder_lows) / len(elder_lows)
    assert avg_low <= 72.0, f"巴菲特晚年 low 均值 {avg_low:.1f} 偏高，老人软化未生效"
    # 但不能低于 DISPLAY_MIN
    for v in elder_lows:
        assert v >= DISPLAY_MIN
