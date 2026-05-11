"""Phase 4-2 新增：cities 200+ 城测试。"""
from src.cities import CITIES, true_solar_time_offset_minutes


def test_at_least_200_cities():
    assert len(CITIES) >= 200, f"应至少 200 城，当前 {len(CITIES)}"


def test_capitals_present():
    must_have = ["北京", "上海", "广州", "深圳", "成都", "杭州", "西安",
                 "武汉", "郑州", "长沙", "重庆", "天津", "南京", "济南",
                 "拉萨", "乌鲁木齐", "海口", "香港", "台北"]
    for c in must_have:
        assert c in CITIES, f"缺少省会/直辖: {c}"


def test_overseas_for_test_charts():
    # 用于历史命盘测试
    for c in ["旧金山", "比勒陀利亚", "奥马哈", "纽约", "东京", "首尔"]:
        assert c in CITIES, f"缺少海外测试城市: {c}"


def test_longitude_range():
    # 中国大陆经度范围 73-135；含海外整体 -180 ~ 180
    for name, info in CITIES.items():
        lon = info["longitude"]
        assert -180 <= lon <= 180, f"{name} longitude {lon} out of range"
        lat = info["latitude"]
        assert -90 <= lat <= 90, f"{name} latitude {lat} out of range"


def test_solar_time_offsets():
    # 北京 116.41° → (116.41-120)*4 = -14.36 min
    assert abs(true_solar_time_offset_minutes(CITIES["北京"]["longitude"]) - (-14.36)) < 0.1
    # 喀什 75.99° → (75.99-120)*4 ≈ -176.04 min
    assert abs(true_solar_time_offset_minutes(CITIES["喀什"]["longitude"]) - (-176.04)) < 0.1
    # 上海 121.47° → +5.88 min
    assert abs(true_solar_time_offset_minutes(CITIES["上海"]["longitude"]) - 5.88) < 0.1
