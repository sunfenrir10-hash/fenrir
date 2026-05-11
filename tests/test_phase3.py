"""Phase 3 测试：黑名单过滤 + LLM mock + FastAPI 集成。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.narrative_sanitize import sanitize_narrative, has_blacklist_word, truncate_to_limit
from src.llm import call_llm, is_mock_mode
from src.pipeline import pipeline
from api.main import app


# ============================================================
# 黑名单过滤
# ============================================================

def test_blacklist_replaces_death_terms():
    """死亡/凶险类关键词应被替换。"""
    raw = "命主晚年遭遇大限，2010 年有血光之灾，险些病死。"
    out = sanitize_narrative(raw)
    assert "大限" not in out
    assert "血光" not in out
    assert "病死" not in out
    assert "死" not in out
    assert not has_blacklist_word(out)
    # 替换后应仍有内容（不是删整段）
    assert len(out) >= 10


def test_blacklist_keeps_neutral_text():
    """正常文本不应被改动。"""
    raw = "整体走势震荡向上，2008 年是一波明显的上升通道。"
    out = sanitize_narrative(raw)
    assert out == raw


def test_blacklist_long_word_priority():
    """长词优先：'病死' 应整体替换为 '健康关注期'，不能先替 '死'。"""
    raw = "病死"
    out = sanitize_narrative(raw)
    assert out == "健康关注期"


# ============================================================
# LLM mock 模式
# ============================================================

def test_llm_mock_mode_when_no_key(monkeypatch):
    """无 KIMI_API_KEY 时走 mock，返回固定文本。"""
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    assert is_mock_mode() is True

    r = pipeline(1991, 5, 12, 8, 0, "北京", gender=1)
    text = call_llm(r["chart"], r["kline"])
    # mock 短卡 80-130 字
    assert 30 <= len(text) <= 200
    # 应含至少一个金融/K线术语
    keywords = ["上升通道", "震荡", "突破", "调整", "牛市", "熊市", "支撑位", "压力位",
                "放量", "洗盘", "回调", "横盘", "箱体", "熔断", "回踩", "变盘"]
    assert any(k in text for k in keywords), f"mock 文本缺少 K 线术语: {text[:80]}"
    # 已经过黑名单过滤，不应有死亡词
    assert not has_blacklist_word(text)


def test_llm_mock_no_markdown():
    """mock 输出无 Markdown 标记/分点/标题。"""
    r = pipeline(1991, 5, 12, 8, 0, "北京", gender=1)
    text = call_llm(r["chart"], r["kline"])
    forbidden = ["##", "**", "```"]
    for f in forbidden:
        assert f not in text, f"mock 文本含禁止 Markdown 结构 '{f}': {text[:80]}"


def test_llm_mock_starts_with_personality_emoji():
    """新短卡格式：mock 必须以 emoji + 标签名开头。"""
    r = pipeline(1991, 5, 12, 8, 0, "北京", gender=1)
    text = call_llm(r["chart"], r["kline"])
    # 第一个字应是 emoji（非中文/非 ASCII）
    assert text[0] not in "abcdefghijklmnopqrstuvwxyz各整命大"
    assert "：" in text[:20]  # 标签后跟全角冒号


# ============================================================
# FastAPI 集成
# ============================================================

@pytest.fixture
def client():
    return TestClient(app)


def test_api_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_chart_basic(client):
    """POST /api/chart 端到端：1991 北京。"""
    r = client.post("/api/chart", json={
        "birth_date": "1991-05-12",
        "birth_time": "08:00",
        "city": "北京",
        "gender": 1,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "kline" in data
    assert len(data["kline"]) == 100
    assert "narrative" in data and len(data["narrative"]) >= 30
    # 短卡限长（含 emoji 等非中文字符，宽限到 130 字符）
    cn_len = sum(1 for c in data["narrative"] if "\u4e00" <= c <= "\u9fff")
    assert cn_len <= 130, f"narrative 中文字数 {cn_len} > 130"
    assert data["meta"]["bazi"] == ["辛未", "癸巳", "壬午", "甲辰"]
    assert data["meta"]["strength"] in ("strong", "balanced", "weak")
    # 新增 personality 字段
    p = data["meta"]["personality"]
    assert p["id"] in range(1, 13)
    assert p["name"] and p["emoji"] and p["tagline"]
    # 美化约束
    for c in data["kline"]:
        assert 30 <= c["open"] <= 95
        assert 30 <= c["close"] <= 95


def test_api_chart_invalid_city(client):
    """Phase 4-2 修复：未知城市不再抛 4xx，改为 fallback 到北京。"""
    r = client.post("/api/chart", json={
        "birth_date": "1991-05-12",
        "birth_time": "08:00",
        "city": "火星基地",
        "gender": 1,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["city_match_type"] == "fallback"
    assert body["meta"]["city_used"] == "北京"
    assert body["meta"]["city_input"] == "火星基地"


def test_api_chart_invalid_date(client):
    r = client.post("/api/chart", json={
        "birth_date": "1991-13-99",
        "birth_time": "08:00",
        "city": "北京",
        "gender": 1,
    })
    # pydantic 验证失败 → 422
    assert r.status_code in (400, 422)


def test_api_chart_narrative_no_blacklist(client):
    """API 返回的 narrative 必须经过黑名单过滤。"""
    r = client.post("/api/chart", json={
        "birth_date": "1930-08-30",
        "birth_time": "15:00",
        "city": "奥马哈",
        "gender": 1,
    })
    assert r.status_code == 200
    text = r.json()["narrative"]
    assert not has_blacklist_word(text)


# ============================================================
# truncate_to_limit 硬截断
# ============================================================

def _cn_count(s: str) -> int:
    return sum(1 for c in s if "\u4e00" <= c <= "\u9fff")


def test_truncate_short_text_unchanged():
    """短文本不动。"""
    raw = "🎯 价值龙头：起步就高开。" * 5  # ~约 75 中文字
    assert _cn_count(raw) <= 120
    assert truncate_to_limit(raw, limit=120) == raw


def test_truncate_long_text_to_120():
    """长文本截到 130 内并以标点结尾。"""
    # 构造 200 字带句号的中文
    sentence = "命主走势震荡向上，前期蓄力后期发力。"  # 18 中文字 + 标点
    raw = sentence * 12  # ~216 中文字
    assert _cn_count(raw) > 120
    out = truncate_to_limit(raw, limit=120, hard_max=130)
    cn = _cn_count(out)
    assert cn <= 130, f"truncated cn={cn}"
    # 应以句末标点结尾
    assert out[-1] in "。！？；!?;", f"末尾字符: {out[-1]!r}"


def test_truncate_no_punctuation_fallback():
    """无标点时硬截到 hard_max 并补句号。"""
    raw = "命" * 200  # 200 个 '命'，无任何标点
    out = truncate_to_limit(raw, limit=120, hard_max=130)
    cn = _cn_count(out)
    assert cn <= 131  # hard_max 130 + 句号
    assert out.endswith("。")


def test_truncate_preserve_ending_keyword():
    """收尾词在 limit 范围内时应完整保留。"""
    raw = "👑 价值龙头：" + "你这盘起步高开。" * 8 + "评级：长期持有，别瞎折腾。"
    # 后缀 "评级：长期持有，别瞎折腾。" 含中文 12 字
    # 8 * 7 = 56 中文字 + 4（前缀） + 12 = 72，不超
    out = truncate_to_limit(raw, limit=120, hard_max=130)
    if _cn_count(raw) <= 120:
        assert out == raw  # 无需截断


def test_call_llm_mock_truncated_within_limit(monkeypatch):
    """mock 模式下输出也应被截到 130 内。"""
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    r = pipeline(1991, 5, 12, 8, 0, "北京")
    text = call_llm(r["chart"], r["kline"], yearly_raw=r["yearly_raw"])
    assert _cn_count(text) <= 130
