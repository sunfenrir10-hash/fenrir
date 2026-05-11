"""端到端 pipeline：输入生日 → 输出 100 根 K 线。"""
from __future__ import annotations

from typing import Literal

from .bazi import compute_bazi, BaziChart
from .score import compute_century_scores
from .sanitize import sanitize_monthly_matrix, apply_elder_soften
from .kline import build_kline
from .strength import classify_strength, favor_multipliers


def pipeline(
    year: int, month: int, day: int,
    hour: int, minute: int,
    city: str,
    gender: Literal[0, 1] = 1,
    horizon_years: int = 100,
) -> dict:
    """主入口：生日 + 出生地 → 100 根 K 线 + 命盘摘要 + 旺衰判定。"""
    chart = compute_bazi(year, month, day, hour, minute, city,
                         gender=gender, horizon_years=horizon_years)

    # Phase 2 新增：日主旺衰判定
    strength_label, strength_raw = classify_strength(chart)
    favor = favor_multipliers(strength_label)

    yearly = compute_century_scores(chart, horizon_years=horizon_years, favor=favor)

    raw_matrix = [y["monthly_scores"] for y in yearly]
    display_matrix = sanitize_monthly_matrix(raw_matrix)

    ages = [y["age"] for y in yearly]
    # Phase 3 老人软化：age > 70 时下压月最低值
    display_matrix = apply_elder_soften(display_matrix, ages)

    kline = build_kline(display_matrix, base_year=chart.solar_birth.year, ages=ages)

    return {
        "chart": {
            "four_pillars": {
                "year": chart.year_pillar.ganzhi,
                "month": chart.month_pillar.ganzhi,
                "day": chart.day_pillar.ganzhi,
                "hour": chart.hour_pillar.ganzhi,
            },
            "day_master": f"{chart.day_master_gan}{chart.day_master_element}",
            "strength": strength_label,
            "strength_raw": round(strength_raw, 2),
            "favor": favor,
            "start_age": chart.start_age,
            "is_forward": chart.is_forward,
            "dayun": [
                {"start_age": d.start_age, "end_age": d.end_age,
                 "start_year": d.start_year, "ganzhi": d.ganzhi}
                for d in chart.dayun_list
            ],
            "true_solar_time": chart.true_solar_birth.strftime("%Y-%m-%d %H:%M"),
            "city": chart.city,
            "longitude": chart.longitude,
            "gender": chart.gender,
        },
        "yearly_raw": yearly,
        "kline": kline,
    }
