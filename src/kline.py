"""月度分数 -> K 线 OHLC 映射。

输入: 100 年的月度分数矩阵（已 sanitize）
输出: 100 根 K 线
"""
from __future__ import annotations

import statistics

VOLUME_SCALE = 10.0  # volume = stdev × 此常数


def build_kline(yearly_month_scores: list[list[float]],
                base_year: int = 0,
                ages: list[int] | None = None) -> list[dict]:
    """构建 K 线序列。

    参数:
        yearly_month_scores: [[12 个月分数], ...] × 100 年（已 sanitize 的展示分）
        base_year: 起始公历年（用于标注每根 K 线对应年份）
        ages: 与年对应的虚岁数组；若 None 则默认 1..N

    返回:
        每根 K 线 dict: {
            "year": int,
            "age": int,
            "open": float,        # 正月
            "close": float,       # 腊月
            "high": float,
            "low": float,
            "volume": float,
            "color": "red" | "green",
        }
    """
    out: list[dict] = []
    for idx, months in enumerate(yearly_month_scores):
        if len(months) != 12:
            raise ValueError(f"第 {idx} 年月度分数长度 != 12: {len(months)}")
        open_v = months[0]
        close_v = months[-1]
        high_v = max(months)
        low_v = min(months)
        vol = statistics.pstdev(months) * VOLUME_SCALE
        color = "red" if close_v > open_v else ("green" if close_v < open_v else "doji")
        y = base_year + idx if base_year else 0
        age = ages[idx] if ages and idx < len(ages) else (idx + 1)
        out.append({
            "year": y,
            "age": age,
            "open": round(open_v, 2),
            "close": round(close_v, 2),
            "high": round(high_v, 2),
            "low": round(low_v, 2),
            "volume": round(vol, 2),
            "color": color,
        })
    return out
