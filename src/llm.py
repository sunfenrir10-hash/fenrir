"""Kimi LLM 集成 + Mock 模式（Phase 3.5：标签 + 短卡）。

无 KIMI_API_KEY 时自动走 mock 模式。
"""
from __future__ import annotations

import os
from typing import Any

from .prompt import build_messages
from .narrative_sanitize import sanitize_narrative, truncate_to_limit
from .personality import detect_personality, extract_highlight_years


KIMI_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "moonshot-v1-32k"
DEFAULT_TEMPERATURE = 0.85  # 略高一点鼓励段子手风


def _mock_narrative(personality: dict, highlights: dict) -> str:
    """构造 mock 叙事，遵守 phase 3.5 短卡格式。"""
    h = highlights.get("high", {})
    l = highlights.get("low", {})
    t = highlights.get("turn", {})
    return (
        f"{personality['emoji']} {personality['name']}：起步震荡，"
        f"{l.get('age', 30)} 岁触发熔断，"
        f"{t.get('age', 50)} 岁急速变盘比劫年回踩，"
        f"{h.get('age', 70)} 岁放量突破创新高。"
        f"建议长期持有，别频繁交易。"
    )


def call_llm(
    chart: dict,
    kline: list[dict],
    *,
    personality: dict | None = None,
    highlights: dict | None = None,
    yearly_raw: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    api_key: str | None = None,
    sanitize: bool = True,
    ending_keyword: str | None = None,
) -> str:
    """调用 Kimi 生成短卡叙事。无 Key 时走 mock。

    若 personality / highlights 未传入，会自动从 kline 计算。
    ending_keyword: 指定收尾词；None 时由 prompt 层随机轮换 5 选 1。
    """
    if personality is None:
        personality = detect_personality(kline)
    if highlights is None:
        highlights = extract_highlight_years(kline)

    key = api_key if api_key is not None else os.getenv("KIMI_API_KEY", "").strip()
    messages = build_messages(chart, kline, personality, highlights, yearly_raw, ending_keyword=ending_keyword)

    if not key:
        text = _mock_narrative(personality, highlights)
    else:
        text = _call_kimi(messages, model=model, temperature=temperature, api_key=key)

    if sanitize:
        text = sanitize_narrative(text)
        text = truncate_to_limit(text, limit=120, hard_max=130)
    return text


def _call_kimi(
    messages: list[dict],
    *,
    model: str,
    temperature: float,
    api_key: str,
) -> str:
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("openai SDK 未安装。请 `pip install openai`") from e

    client = OpenAI(api_key=api_key, base_url=KIMI_BASE_URL)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def is_mock_mode() -> bool:
    return not os.getenv("KIMI_API_KEY", "").strip()
