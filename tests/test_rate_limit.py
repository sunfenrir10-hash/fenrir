"""速率限制测试（slowapi）。

场景：同一 IP 1 分钟内对 /api/chart 第 6 次请求应返回 429 + 友好文案。
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client_ratelimited(monkeypatch):
    """开启限流，重新加载 api.main 让模块级 limiter.enabled=True。"""
    monkeypatch.setenv("MINGK_RATELIMIT", "1")
    # slowapi 用模块级 Limiter，必须 reload 才能让 enabled 生效
    import api.main as m
    importlib.reload(m)
    yield TestClient(m.app)
    # 回滚（避免污染其它测试）
    monkeypatch.setenv("MINGK_RATELIMIT", "0")
    importlib.reload(m)


def _payload():
    return {
        "birth_date": "1991-05-12",
        "birth_time": "08:00",
        "city": "北京",
        "gender": 1,
    }


def test_chart_rate_limit_5_per_minute(client_ratelimited):
    """前 5 次 200，第 6 次 429。"""
    ok = 0
    for i in range(5):
        r = client_ratelimited.post("/api/chart", json=_payload())
        assert r.status_code == 200, f"第 {i+1} 次应 200，实际 {r.status_code}"
        ok += 1
    assert ok == 5

    r6 = client_ratelimited.post("/api/chart", json=_payload())
    assert r6.status_code == 429
    body = r6.json()
    assert "请求太频繁" in body["detail"]
    assert body["retry_after_seconds"] == 60


def test_healthz_not_rate_limited(client_ratelimited):
    """/healthz 不限流（运行健康检查/CDN ping）。"""
    for _ in range(20):
        r = client_ratelimited.get("/healthz")
        assert r.status_code == 200
