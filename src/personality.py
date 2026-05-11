"""K 线人格标签判定（Phase 3.5）。

12 种标签按优先级判定，第一个匹配即终。兜底为 12 号"均衡白马"。

输入: list[KLineCandle] — 100 根 K 线 dict（含 close/high/low/year/age/color）
输出: {"id", "name", "emoji", "tagline"} 单一标签

标签判定规则严格按 plan 文档；阈值集中在顶部常量便于调参。
"""
from __future__ import annotations

import statistics
from typing import Any


# ============================================================
# 12 标签定义（顺序即优先级）
# ============================================================
PERSONALITIES: list[dict] = [
    {"id": 1,  "name": "价值龙头",   "emoji": "👑", "tagline": "30 岁达到大多数人 50 岁高度，后面别浪"},
    {"id": 2,  "name": "长牛白马股", "emoji": "🐂", "tagline": "慢慢富的命，巴菲特同款"},
    {"id": 3,  "name": "创业板黑马", "emoji": "🚀", "tagline": "前半生攒经验，40 岁突然狂飙"},
    {"id": 4,  "name": "ST重组股",   "emoji": "💊", "tagline": "一记闷棍后从 ICU 爬起翻身"},
    {"id": 5,  "name": "逆袭黑马股", "emoji": "🦋", "tagline": "草根逆袭剧本"},
    {"id": 6,  "name": "周期股",     "emoji": "🔄", "tagline": "自带节奏，每 10 年一次牛熊"},
    {"id": 7,  "name": "妖股",       "emoji": "🎢", "tagline": "开盘 30 收盘 90 中间 12 次跌停"},
    {"id": 8,  "name": "早慧股",     "emoji": "🌅", "tagline": "早年得志后是细水长流的自我和解"},
    {"id": 9,  "name": "庄股",       "emoji": "🎩", "tagline": "前半段韬光养晦后突然拉盘"},
    {"id": 10, "name": "慢牛仙股",   "emoji": "🐢", "tagline": "涨得不快但从不掉，命运的水电煤"},
    {"id": 11, "name": "守成蓝筹",   "emoji": "🏛️", "tagline": "不刺激，但钱本来就在"},
    {"id": 12, "name": "均衡白马",   "emoji": "💎", "tagline": "长得稳涨得稳活得稳，命理届奢侈品"},
]


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    return statistics.pstdev(xs)


def _count_peak_valley_swings(closes: list[float], min_amp: float = 15.0) -> int:
    """数 close 序列中"峰谷交替"次数，每次峰谷差 >= min_amp 才算一次反转。

    使用"局部极值 + 阈值过滤"算法（处理 plateau）：
    1. 标记每个点为高于/低于其前后 N 邻居的中位线
    2. 找连续上升 → 下降 转折（peak），连续下降 → 上升 转折（valley）
    3. 相邻峰谷差 >= min_amp 计一次 swing
    """
    n = len(closes)
    if n < 5:
        return 0

    # 标记方向：next - prev > 0 → +1 上升, < 0 → -1 下降, == 0 → 0
    # 然后扫描方向变化点
    extrema: list[tuple[int, float, str]] = []  # (idx, value, kind)
    direction = 0  # 1=up, -1=down
    last_extreme_idx = 0
    last_extreme_val = closes[0]
    last_extreme_kind: str | None = None

    for i in range(1, n):
        if closes[i] > last_extreme_val:
            if direction == -1:  # 上一段是 down，刚才的 last_extreme 是 valley
                extrema.append((last_extreme_idx, last_extreme_val, "valley"))
                last_extreme_kind = "valley"
            direction = 1
            last_extreme_idx = i
            last_extreme_val = closes[i]
        elif closes[i] < last_extreme_val:
            if direction == 1:  # 上一段是 up，刚才的 last_extreme 是 peak
                extrema.append((last_extreme_idx, last_extreme_val, "peak"))
                last_extreme_kind = "peak"
            direction = -1
            last_extreme_idx = i
            last_extreme_val = closes[i]
        # closes[i] == last_extreme_val: 维持 plateau，不变
    # 收尾：最后一个 extreme
    if direction == 1:
        extrema.append((last_extreme_idx, last_extreme_val, "peak"))
    elif direction == -1:
        extrema.append((last_extreme_idx, last_extreme_val, "valley"))

    # 数相邻峰谷差 >= min_amp 的次数
    swings = 0
    for a, b in zip(extrema, extrema[1:]):
        if a[2] != b[2] and abs(a[1] - b[1]) >= min_amp:
            swings += 1
    return swings


def _color_red_green_density(kline: list[dict]) -> float:
    """红绿交替密度 = 颜色变化次数 / 长度。"""
    if len(kline) < 2:
        return 0.0
    changes = sum(
        1 for a, b in zip(kline, kline[1:]) if a["color"] != b["color"]
    )
    return changes / (len(kline) - 1)


def detect_personality(kline: list[dict]) -> dict:
    """根据 100 年 K 线判定人格标签。

    参数:
        kline: list[dict]，每项含 close/high/low/year/age/color
    返回:
        {"id", "name", "emoji", "tagline"}
    """
    if not kline:
        return PERSONALITIES[-1].copy()

    closes = [k["close"] for k in kline]
    n = len(closes)
    start = closes[0]
    end = closes[-1]

    sigma = _stdev(closes)
    red_count = sum(1 for k in kline if k["color"] == "red")
    green_count = sum(1 for k in kline if k["color"] == "green")
    rg_ratio = red_count / max(green_count, 1)

    # 1. 价值龙头：18-30 岁出现 close >= 82 且 后期不能下行（否则归早慧 P8）
    #    新约束：30 岁后 70 年均值 >= 前 30 年均值 - 5
    p1_window = [k for k in kline if 18 <= k["age"] <= 30]
    if any(k["close"] >= 82 for k in p1_window) and n >= 30:
        first30_avg = statistics.mean(closes[:30])
        rest_avg = statistics.mean(closes[30:]) if n > 30 else first30_avg
        if rest_avg >= first30_avg - 5:
            return PERSONALITIES[0].copy()

    # 2. 长牛白马股：终>起+20 且 σ<8 且 红:绿>=1.3
    if end > start + 20 and sigma < 8 and rg_ratio >= 1.3:
        return PERSONALITIES[1].copy()

    # 3. 创业板黑马：前 50 年均 + 15 < 后 50 年均
    half = n // 2
    if half >= 5:
        first_half_avg = statistics.mean(closes[:half])
        second_half_avg = statistics.mean(closes[half:])
        if first_half_avg + 15 < second_half_avg:
            return PERSONALITIES[2].copy()

    # 4. ST 重组股：30-80 岁出现 close < 起点-20 且后续反弹回 >= 起点+5
    mid_segment = [(i, c) for i, c in enumerate(closes) if 30 <= kline[i]["age"] <= 80]
    if mid_segment:
        crash_idx = None
        crash_val = None
        for idx, c in mid_segment:
            if c < start - 20:
                if crash_val is None or c < crash_val:
                    crash_idx, crash_val = idx, c
        if crash_idx is not None:
            # 反弹要求：crash 之后任意年 close >= start + 5（真翻身）
            if any(closes[j] >= start + 5 for j in range(crash_idx + 1, n)):
                return PERSONALITIES[3].copy()

    # 5. 逆袭黑马股：起点 < 50 且 终点 > 起点+30
    if start < 50 and end > start + 30:
        return PERSONALITIES[4].copy()

    # 6. 周期股：>= 7 次峰谷反转（幅度>=15）OR 最大峰谷差>=40 且 >=4 次反转
    #    收紧后只匹配真"多周期剧烈波动"，不抢普通起伏
    swing_count = _count_peak_valley_swings(closes, min_amp=15.0)
    max_pv_diff = max(closes) - min(closes)
    if swing_count >= 7 or (max_pv_diff >= 40 and swing_count >= 4):
        return PERSONALITIES[5].copy()

    # 7. 妖股：σ > 12 或 红绿交替密度 > 0.5
    if sigma > 12 or _color_red_green_density(kline) > 0.5:
        return PERSONALITIES[6].copy()

    # 8. 早慧股：前 30 年峰值 > 后 70 年峰值 + 10（加严避免抢周期股）
    if n >= 30:
        first_peak = max(closes[:30])
        rest_peak = max(closes[30:]) if n > 30 else first_peak
        if first_peak > rest_peak + 10:
            return PERSONALITIES[7].copy()

    # 9. 庄股：前 40 年均 < 60 且 后段 close > 80
    if n >= 40:
        first_avg = statistics.mean(closes[:40])
        rest_max = max(closes[40:]) if n > 40 else 0
        if first_avg < 60 and rest_max > 80:
            return PERSONALITIES[8].copy()

    # 10. 慢牛仙股：终 > 起+10 且 σ < 5
    if end > start + 10 and sigma < 5:
        return PERSONALITIES[9].copy()

    # 11. 守成蓝筹：起终差 < 10 且 σ < 8
    if abs(end - start) < 10 and sigma < 8:
        return PERSONALITIES[10].copy()

    # 12. 兜底：均衡白马
    return PERSONALITIES[11].copy()


def extract_highlight_years(kline: list[dict]) -> dict:
    """提取 3 个高光年份给 LLM：最高分年 / 最低分年 / 最大斜率转折年。

    返回每个高光的 {year, age, close, kind}。
    """
    if not kline:
        return {}
    closes = [k["close"] for k in kline]
    n = len(closes)

    high_idx = max(range(n), key=lambda i: closes[i])
    low_idx = min(range(n), key=lambda i: closes[i])

    # 最大斜率转折年：相邻两年 close 差最大的位置（取后一年）
    if n >= 2:
        diffs = [abs(closes[i] - closes[i - 1]) for i in range(1, n)]
        slope_idx = diffs.index(max(diffs)) + 1  # +1 偏移到后一年
    else:
        slope_idx = 0

    return {
        "high": {
            "year": kline[high_idx]["year"],
            "age": kline[high_idx]["age"],
            "close": kline[high_idx]["close"],
        },
        "low": {
            "year": kline[low_idx]["year"],
            "age": kline[low_idx]["age"],
            "close": kline[low_idx]["close"],
        },
        "turn": {
            "year": kline[slope_idx]["year"],
            "age": kline[slope_idx]["age"],
            "close": kline[slope_idx]["close"],
            "delta": round(closes[slope_idx] - closes[slope_idx - 1], 2)
            if slope_idx > 0 else 0.0,
        },
    }
