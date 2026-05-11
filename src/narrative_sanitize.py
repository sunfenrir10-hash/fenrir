"""叙事文本黑名单关键词软化（Phase 3）。

后处理：把命理叙事中可能引起用户不适的"死亡/凶险"类词汇
替换成股评味道的中性表达，而不是删除整段。
保持语义连贯，不破坏原文风格。
"""
from __future__ import annotations

import re

# 替换表：尽量"长词优先"以避免短词先匹配截断
# 例如 "病死" 必须排在 "死" 前面
BLACKLIST_REPLACEMENTS: list[tuple[str, str]] = [
    # 健康/寿元类（最敏感）
    ("病死", "健康关注期"),
    ("病亡", "健康关注期"),
    ("猝死", "突发转折"),
    ("寿终", "收尾"),
    ("仙逝", "人生最后篇章"),
    ("离世", "阶段性归宿"),
    ("身亡", "重大转折"),
    ("夭折", "阶段性收束"),
    ("夭亡", "阶段性收束"),
    ("天年", "晚境"),
    ("阳寿", "命途余韵"),
    ("大限", "阶段性归宿"),
    ("死亡", "转折"),
    ("亡故", "阶段性归宿"),
    ("过世", "阶段性归宿"),
    # 单字"死"放在最后兜底（多字组合已先被替换）
    ("死", "终局"),
    # 凶险类
    ("凶险", "考验"),
    ("血光", "波折"),
    ("灾祸", "重大挑战"),
    ("灾难", "重大挑战"),
    ("劫难", "重大挑战"),
    ("劫数", "考验"),
    ("大凶", "重大调整"),
    ("凶事", "波折"),
    ("祸事", "波折"),
    ("祸患", "波折"),
    ("凶", "挑战"),
    ("厄运", "考验期"),
    ("厄", "考验"),
    ("灾", "挑战"),
    ("难", "考验"),
    # 神煞色彩重的（保守替换）
    ("丧门", "情绪低位"),
    ("吊客", "情绪低位"),
    ("白虎", "波动期"),
]


def sanitize_narrative(text: str) -> str:
    """对 LLM 输出做黑名单软化。

    规则：
      - 顺序遍历替换表（长词在前），逐个 `str.replace`
      - 不删整段，只换词；保持原文连贯
      - 大小写敏感（中文无关；英文场景请自行扩展）

    参数:
        text: 原始叙事文本
    返回:
        软化后文本
    """
    if not text:
        return text
    out = text
    for bad, good in BLACKLIST_REPLACEMENTS:
        out = out.replace(bad, good)
    return out


def has_blacklist_word(text: str) -> bool:
    """检查文本是否仍包含任一黑名单词（用于测试 / 兜底告警）。"""
    if not text:
        return False
    for bad, _ in BLACKLIST_REPLACEMENTS:
        if bad in text:
            return True
    return False


# 句末标点（中英）
_SENTENCE_ENDS = "。！？；!?;"


def _count_chinese(text: str) -> int:
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')


def truncate_to_limit(text: str, limit: int = 120, hard_max: int = 130, min_keep: int = 80) -> str:
    """硬截断中文字符到 limit 内，从末尾向前找最近句末标点。

    规则：
    - 中文字数 <= limit：直接返回
    - 否则向前扫描中文字符到 limit 处，再向左找最近句末标点截断
    - 若截断后中文字数 < min_keep：尝试向前找下一个句末标点（允许 hard_max 字内）
    - 若仍找不到合适标点：直接在 hard_max 字处截断并补"。"
    """
    if not text:
        return text
    if _count_chinese(text) <= limit:
        return text

    # 找到中文字数到达 limit 的字符位置
    cn_count = 0
    cut_pos = len(text)
    for i, c in enumerate(text):
        if '\u4e00' <= c <= '\u9fff':
            cn_count += 1
            if cn_count > limit:
                cut_pos = i
                break

    # 向左找最近句末标点
    best = -1
    for j in range(cut_pos - 1, -1, -1):
        if text[j] in _SENTENCE_ENDS:
            best = j
            break

    if best >= 0:
        candidate = text[: best + 1]
        if _count_chinese(candidate) >= min_keep:
            return candidate

    # 候选太短：尝试在 hard_max 内找句末标点
    cn_count = 0
    hard_pos = len(text)
    for i, c in enumerate(text):
        if '\u4e00' <= c <= '\u9fff':
            cn_count += 1
            if cn_count > hard_max:
                hard_pos = i
                break

    # 在 [cut_pos, hard_pos] 区间向后找最近标点
    for j in range(cut_pos, min(hard_pos, len(text))):
        if text[j] in _SENTENCE_ENDS:
            return text[: j + 1]

    # 仍找不到：在 hard_pos 处硬截 + 补"。"
    truncated = text[:hard_pos].rstrip()
    if truncated and truncated[-1] not in _SENTENCE_ENDS:
        truncated += "。"
    return truncated
