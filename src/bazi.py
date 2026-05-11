"""八字排盘模块。

基于 lunar-python 库，包装为更易用的接口：
- 四柱（年/月/日/时）
- 日主五行
- 大运列表（每步 10 年，共 ~10 步）
- 流年列表（100 年）
- 月柱列表（每年 12 月）

真太阳时修正：钟表时 + (经度 - 时区中央经线) × 4 分钟
（V1 忽略均时差 EoT）
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Literal

from lunar_python import Solar

from .cities import CITIES, true_solar_time_offset_minutes

# 天干 -> 五行
GAN_TO_ELEMENT: dict[str, str] = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

# 地支 -> 五行（主气）
ZHI_TO_ELEMENT: dict[str, str] = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 天干阴阳
GAN_YINYANG: dict[str, str] = {
    "甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴",
    "戊": "阳", "己": "阴", "庚": "阳", "辛": "阴",
    "壬": "阳", "癸": "阴",
}


@dataclass
class Pillar:
    """一柱：干 + 支。"""
    gan: str
    zhi: str

    @property
    def ganzhi(self) -> str:
        return self.gan + self.zhi

    def __str__(self) -> str:
        return self.ganzhi


@dataclass
class DaYun:
    """一步大运（10 年）。"""
    start_age: int
    end_age: int
    start_year: int
    ganzhi: str  # 大运干支，如 "壬辰"

    @property
    def gan(self) -> str:
        return self.ganzhi[0] if self.ganzhi else ""

    @property
    def zhi(self) -> str:
        return self.ganzhi[1] if self.ganzhi else ""


@dataclass
class BaziChart:
    """完整命盘数据。"""
    # 基本信息
    solar_birth: dt.datetime            # 输入的钟表生日时间
    true_solar_birth: dt.datetime       # 真太阳时修正后的时间
    city: str
    longitude: float
    gender: Literal[0, 1]               # 1=男 0=女

    # 四柱
    year_pillar: Pillar
    month_pillar: Pillar
    day_pillar: Pillar
    hour_pillar: Pillar

    # 日主
    day_master_gan: str                 # 日干，如 "壬"
    day_master_element: str             # 日主五行，如 "水"

    # 命盘地支列表（年月日时），用于流年地支关系判定
    natal_zhi_list: list[str] = field(default_factory=list)

    # 起运
    start_age: int = 0                  # 起运虚岁
    is_forward: bool = True             # 是否顺行

    # 大运（最多 10 步 = 100 年）
    dayun_list: list[DaYun] = field(default_factory=list)

    # 流年：{year: ganzhi}，100 年
    liunian_map: dict[int, str] = field(default_factory=dict)

    # 流月：{year: [(month_int, ganzhi), ... 12 项]}
    liuyue_map: dict[int, list[tuple[int, str]]] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------

def _nearest_timezone_meridian(longitude: float) -> float:
    """按经度推断所在时区的中央经线（15° 的整数倍）。

    这是近似做法。正式项目应让用户选时区；V1 对几个测试城市够用：
      - 北京 116.41 -> 120 (UTC+8)
      - 旧金山 -122.42 -> -120 (UTC-8)
      - 比勒陀利亚 28.19 -> 30 (UTC+2)
      - 东京 139.69 -> 135 (UTC+9)
    """
    return round(longitude / 15.0) * 15.0


def _apply_true_solar_time(
    clock_time: dt.datetime, longitude: float
) -> dt.datetime:
    """钟表时 -> 真太阳时（仅经度修正，忽略 EoT）。"""
    tz_meridian = _nearest_timezone_meridian(longitude)
    offset_min = true_solar_time_offset_minutes(longitude, tz_meridian)
    return clock_time + dt.timedelta(minutes=offset_min)


# -----------------------------------------------------------------------------
# 主排盘函数
# -----------------------------------------------------------------------------

def compute_bazi(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    city: str,
    gender: Literal[0, 1] = 1,
    horizon_years: int = 100,
) -> BaziChart:
    """计算完整命盘。

    参数:
        year/month/day/hour/minute: 公历钟表时（出生地当地时区）
        city: 城市名（必须在 cities.CITIES 中）
        gender: 1=男 0=女（影响大运顺逆）
        horizon_years: 流年/流月回推年数（默认 100）

    返回:
        BaziChart 对象，包含四柱、日主、大运、流年、流月。
    """
    if city not in CITIES:
        raise KeyError(f"未知城市: {city}")
    longitude = CITIES[city]["longitude"]

    clock = dt.datetime(year, month, day, hour, minute, 0)
    true_solar = _apply_true_solar_time(clock, longitude)

    # 用真太阳时排盘
    solar = Solar.fromYmdHms(
        true_solar.year, true_solar.month, true_solar.day,
        true_solar.hour, true_solar.minute, 0
    )
    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    year_p = Pillar(ec.getYearGan(), ec.getYearZhi())
    month_p = Pillar(ec.getMonthGan(), ec.getMonthZhi())
    day_p = Pillar(ec.getDayGan(), ec.getDayZhi())
    hour_p = Pillar(ec.getTimeGan(), ec.getTimeZhi())

    day_master_gan = day_p.gan
    day_master_element = GAN_TO_ELEMENT[day_master_gan]

    # 大运
    yun = ec.getYun(gender)
    dayun_raw = yun.getDaYun()
    dayun_list: list[DaYun] = []
    for d in dayun_raw:
        gz = d.getGanZhi()
        if not gz:
            # index=0 是未起运的童限段，跳过
            continue
        dayun_list.append(
            DaYun(
                start_age=d.getStartAge(),
                end_age=d.getEndAge(),
                start_year=d.getStartYear(),
                ganzhi=gz,
            )
        )

    # 流年：从出生年开始，扫 horizon_years 年
    liunian_map: dict[int, str] = {}
    liuyue_map: dict[int, list[tuple[int, str]]] = {}
    for offset in range(horizon_years):
        y = year + offset
        # 流年干支：取当年立春后的年柱（lunar-python 内部按节气分）
        # 简化用 y 年 6 月 1 日定位到该年的年柱
        sol_y = Solar.fromYmd(y, 6, 1)
        lun_y = sol_y.getLunar()
        liunian_gz = lun_y.getYearInGanZhi()
        liunian_map[y] = liunian_gz

        # 流月：取每个月的月中（15 日）的月柱
        months: list[tuple[int, str]] = []
        for m in range(1, 13):
            sol_m = Solar.fromYmd(y, m, 15)
            lun_m = sol_m.getLunar()
            months.append((m, lun_m.getMonthInGanZhi()))
        liuyue_map[y] = months

    return BaziChart(
        solar_birth=clock,
        true_solar_birth=true_solar,
        city=city,
        longitude=longitude,
        gender=gender,
        year_pillar=year_p,
        month_pillar=month_p,
        day_pillar=day_p,
        hour_pillar=hour_p,
        day_master_gan=day_master_gan,
        day_master_element=day_master_element,
        natal_zhi_list=[year_p.zhi, month_p.zhi, day_p.zhi, hour_p.zhi],
        start_age=dayun_list[0].start_age if dayun_list else 0,
        is_forward=yun.isForward(),
        dayun_list=dayun_list,
        liunian_map=liunian_map,
        liuyue_map=liuyue_map,
    )


def get_dayun_for_age(chart: BaziChart, age: int) -> DaYun | None:
    """找到指定虚岁对应的大运。"""
    for d in chart.dayun_list:
        if d.start_age <= age <= d.end_age:
            return d
    return None


def get_dayun_for_year(chart: BaziChart, year: int) -> DaYun | None:
    """找到指定公历年对应的大运。"""
    for d in chart.dayun_list:
        if d.start_year <= year < d.start_year + 10:
            return d
    return None
