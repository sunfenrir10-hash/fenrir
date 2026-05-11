"""分数美化铁律。

- 原始分 [-100, +100] -> 展示分 [30, 95]
- 任意相邻两根 close 跌幅 ≤ 30%
- 100 年全画满（不做"晚年"灰化）
- 老人软化（age > 70）：把当年月最低值再下压 N 分，避免画面"老人不老"违和
"""
from __future__ import annotations

DISPLAY_MIN: float = 30.0
DISPLAY_MAX: float = 95.0
MAX_DROP_RATIO: float = 0.30  # 相邻 close 最大跌幅

# 老人软化（Phase 3 新增）
ELDER_AGE_THRESHOLD: int = 70    # 超过此年龄启用下压
ELDER_PUSH_DOWN_DEFAULT: float = 6.0  # 月最低值下压默认幅度（5-8 之间）


def _linear_map(x: float, src_lo: float = -100.0, src_hi: float = 100.0,
                dst_lo: float = DISPLAY_MIN, dst_hi: float = DISPLAY_MAX) -> float:
    """线性映射并 clip。"""
    if x < src_lo:
        x = src_lo
    elif x > src_hi:
        x = src_hi
    ratio = (x - src_lo) / (src_hi - src_lo)
    return dst_lo + ratio * (dst_hi - dst_lo)


def sanitize(raw_scores: list[float]) -> list[float]:
    """美化一维分数序列。

    步骤:
        1. [-100, +100] -> [30, 95] 线性映射
        2. 跌幅限制：若 today < yesterday × 0.7，则抬升到 yesterday × 0.7
        3. 最终 clip 到 [30, 95]

    参数:
        raw_scores: 原始分数列表（通常是 100 年的 close，或 12 个月的月度分）
    返回:
        同长度的展示分数列表
    """
    if not raw_scores:
        return []

    # 1. 映射
    mapped = [_linear_map(x) for x in raw_scores]

    # 2. 跌幅限制
    floored: list[float] = [mapped[0]]
    for i in range(1, len(mapped)):
        cur = mapped[i]
        prev = floored[i - 1]
        min_allowed = prev * (1.0 - MAX_DROP_RATIO)
        if cur < min_allowed:
            cur = min_allowed
        floored.append(cur)

    # 3. clip
    clipped = [max(DISPLAY_MIN, min(DISPLAY_MAX, v)) for v in floored]
    return clipped


def sanitize_monthly_matrix(raw_matrix: list[list[float]]) -> list[list[float]]:
    """对 100 年 × 12 月矩阵做美化。

    策略：
        a. 先把 100 年的月度分"展平"成 1200 点线性序列做整体映射
        b. 映射完再逐年切回 12 个月
        c. 在"年 close（= 腊月）"序列上做跌幅限制，并把该行整体平移以维持约束
           （平移量 = 需要抬升的 close 差值；月内 O/H/L 同步平移）

    这样 K 线的月内波动保留，年际跌幅受限。
    """
    if not raw_matrix:
        return []

    # a. 展平线性映射
    mapped_matrix: list[list[float]] = [
        [_linear_map(x) for x in months] for months in raw_matrix
    ]

    # b. 取每年 close（最后一月）做跌幅约束，计算每年需要的 shift
    closes = [year[-1] for year in mapped_matrix]
    shifts: list[float] = [0.0]  # 第一年不动
    adjusted_closes = [closes[0]]
    for i in range(1, len(closes)):
        prev_close = adjusted_closes[-1]
        min_allowed = prev_close * (1.0 - MAX_DROP_RATIO)
        raw_close = closes[i]
        shift = 0.0
        if raw_close < min_allowed:
            shift = min_allowed - raw_close
        shifts.append(shift)
        adjusted_closes.append(raw_close + shift)

    # c. 把 shift 同时作用到该年所有 12 个月，并 clip 到 [30, 95]
    out: list[list[float]] = []
    for year_idx, months in enumerate(mapped_matrix):
        s = shifts[year_idx]
        shifted = [max(DISPLAY_MIN, min(DISPLAY_MAX, v + s)) for v in months]
        out.append(shifted)
    return out


def apply_elder_soften(
    matrix: list[list[float]],
    ages: list[int],
    *,
    threshold: int = ELDER_AGE_THRESHOLD,
    push_down: float = ELDER_PUSH_DOWN_DEFAULT,
) -> list[list[float]]:
    """老人软化：当 age > threshold 时，对该年 12 个月里最低的那个月再下压 push_down 分。

    约束：
      - 不得突破美化下限 30
      - 不得让该年 close 比上一年 close 多跌超过 MAX_DROP_RATIO
        若违反则按比例缩小本次下压幅度
      - 月内其余值（含 close）不动 → 仅影响 K 线的 low（避免老人画面分数仍过高）

    输入: 已 sanitize 过的 100 × 12 矩阵 + 同长度的 ages
    输出: 同形矩阵
    """
    if not matrix:
        return []
    if len(matrix) != len(ages):
        raise ValueError(f"matrix len {len(matrix)} != ages len {len(ages)}")

    out: list[list[float]] = [list(row) for row in matrix]

    for i, (months, age) in enumerate(zip(out, ages)):
        if age <= threshold:
            continue
        # 找最低月
        low_idx = min(range(12), key=lambda k: months[k])
        cur_low = months[low_idx]

        # 下压目标
        target = cur_low - push_down

        # 约束 1：不突破 DISPLAY_MIN
        if target < DISPLAY_MIN:
            target = DISPLAY_MIN

        # 约束 2：不让 close 跌幅超 30%（low 下压不影响 close，但稳妥起见也校验）
        # close 是月 11，本规则不动 close，所以不会破坏跌幅约束。
        # 但若 low 在最后一月（罕见），需要保护
        if low_idx == 11 and i > 0:
            prev_close = out[i - 1][-1]
            min_allowed = prev_close * (1.0 - MAX_DROP_RATIO)
            if target < min_allowed:
                target = min_allowed

        # 应用
        if target < cur_low:
            out[i][low_idx] = target

    return out
