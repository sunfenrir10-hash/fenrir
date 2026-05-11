"""resolve_city 单测（Phase 4-2 修复 1：城市自由输入）。"""

from src.cities import CITIES, resolve_city, _normalize


def test_normalize_strip_suffix():
    assert _normalize("北京市") == "北京"
    assert _normalize("乌鲁木齐市") == "乌鲁木齐"
    assert _normalize("延边朝鲜族自治州") == "延边朝鲜族"
    assert _normalize("内蒙古自治区") == "内蒙古"
    assert _normalize("  深圳  ") == "深圳"
    assert _normalize("") == ""


def test_resolve_exact_plain():
    r = resolve_city("北京")
    assert r is not None
    assert r["name"] == "北京"
    assert r["matched"] == "exact"
    assert "longitude" in r


def test_resolve_exact_with_suffix():
    """带"市"后缀，normalize 后应精确匹配。"""
    r = resolve_city("北京市")
    assert r is not None
    assert r["name"] == "北京"
    assert r["matched"] == "exact"


def test_resolve_with_whitespace():
    r = resolve_city("  深圳  ")
    assert r is not None
    assert r["name"] == "深圳"
    assert r["matched"] == "exact"


def test_resolve_huaihua():
    """怀化：263 城里如果有就 exact，否则 fuzzy（湖南地级市，常用）。"""
    r = resolve_city("怀化")
    if "怀化" in CITIES:
        assert r is not None
        assert r["name"] == "怀化"
        assert r["matched"] == "exact"
    else:
        # 至少不能 None（应模糊命中某个城市）— 但若 cutoff=0.6 仍找不到也允许 None
        # 这里只断言不抛异常；返回 None 也算 fallback 路径
        assert r is None or r["matched"] in ("fuzzy", "exact")


def test_resolve_huaihua_with_suffix():
    r1 = resolve_city("怀化")
    r2 = resolve_city("怀化市")
    # 两次结果应一致（normalize 把"市"去掉了）
    if r1 is None:
        assert r2 is None or r2["matched"] == "fuzzy"
    else:
        assert r2 is not None
        assert r2["name"] == r1["name"]


def test_resolve_urumqi():
    r = resolve_city("乌鲁木齐")
    assert r is not None
    assert r["name"] == "乌鲁木齐"
    assert r["matched"] == "exact"


def test_resolve_random_garbage():
    """瞎敲完全无法识别。"""
    assert resolve_city("瞎敲abcdef") is None
    assert resolve_city("xkcdz9991") is None


def test_resolve_empty_input():
    assert resolve_city("") is None
    assert resolve_city("   ") is None
    assert resolve_city(None) is None  # 容错：None 不应抛


def test_resolve_overseas_or_fuzzy():
    """旧金山/比勒陀利亚/奥马哈：263 城里不一定有，应优雅处理。"""
    for name in ["旧金山", "比勒陀利亚", "奥马哈"]:
        r = resolve_city(name)
        # 不抛异常即可；命中 exact/fuzzy/None 都算可接受
        assert r is None or r["matched"] in ("exact", "fuzzy", "alias")


# ============================================================
# 补充测试：city_db ≥ 300 + alias（拼音/英文/简繁/历史名）
# ============================================================
def test_city_db_size_ge_300():
    """city_db 至少 300 条。"""
    assert len(CITIES) >= 300, f"实际 {len(CITIES)} < 300"


def test_resolve_pinyin_urumqi():
    """Urumqi 拼音应通过 alias 解析到乌鲁木齐。"""
    r = resolve_city("Urumqi")
    assert r is not None
    assert r["name"] == "乌鲁木齐"
    assert r["matched"] == "alias"


def test_resolve_pinyin_lower():
    """全小写拼音也行。"""
    for inp, expect in [("beijing", "北京"), ("shanghai", "上海"), ("hk", "香港")]:
        r = resolve_city(inp)
        assert r is not None and r["name"] == expect and r["matched"] == "alias"


def test_resolve_traditional_chinese():
    """简繁转换：臺北 → 台北、廣州 → 广州。"""
    r = resolve_city("臺北")
    assert r is not None and r["name"] == "台北" and r["matched"] == "alias"
    r2 = resolve_city("廣州")
    assert r2 is not None and r2["name"] == "广州" and r2["matched"] == "alias"


def test_resolve_historical_name():
    """历史名 / 别称：金陵 → 南京、燕京 → 北京。"""
    assert resolve_city("金陵")["name"] == "南京"
    assert resolve_city("燕京")["name"] == "北京"
    assert resolve_city("魔都")["name"] == "上海"


def test_resolve_jiaxing_and_huaihua_county_level():
    """三四线 / 县级市常见输入。"""
    assert resolve_city("嘉兴")["name"] == "嘉兴"
    assert resolve_city("怀化市")["name"] == "怀化"
    assert resolve_city("昆山")["name"] == "昆山"
