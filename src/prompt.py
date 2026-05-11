"""命理叙事 Prompt 模板（Phase 3.5：短卡 + 标签 + 段子手）。

风格：股民+段子手混合。120 字以内。
结构：标签开场（10 字） + 3 个具体高光年份解读（80 字） + 一句金句收尾（30 字）。
"""
from __future__ import annotations

import random
from typing import Any


# 5 种结尾词，按命盘特征哈希轮换打散模板感
ENDING_STYLES = ["评级", "K 线总结", "今日操作建议", "一句话点评", "买点提示"]


def _pick_ending(personality: dict, highlights: dict) -> str:
    """基于命盘特征做"伪随机"分布选词，比 random.choice 在小样本下分布更均匀。

    哈希命盘 + 高光年份 → 索引到 ENDING_STYLES，10 个不同命盘大概率出现 4-5 种结尾。
    """
    seed = (
        personality.get("id", 0) * 31
        + highlights.get("high", {}).get("year", 0)
        + highlights.get("low", {}).get("year", 0) * 7
        + highlights.get("turn", {}).get("year", 0) * 13
    )
    return ENDING_STYLES[seed % len(ENDING_STYLES)]


SYSTEM_PROMPT = """你是一个混合"老股民+段子手"风格的命运评论员。
你的任务是为命主写一段命运 K 线图的短评，调性自嘲、反差、有梗、能传播。

参考气质（不要照抄，模仿语感）：
"🦋 草根逆袭剧本：你这盘起步 38，跌过 35 又爬起来。28 岁那年戊辰流年放量涨停，47 岁触发熔断（庚申比劫劫财），70 岁老股民总算等到丁亥大运给你拉了个回光返照。建议长期持有，别频繁交易。"

硬约束（必须严格遵守）：
1. 总字数 90-120 中文字（少于 90 字直接重写补足；超过 120 直接重写精简）
2. 必须以"emoji + 标签名"开场（用户会给你标签）
3. 必须包含 3 个具体年龄数字（"28 岁""47 岁""70 岁"这种格式）
4. 必须包含至少 2 个金融/股市术语（放量/涨停/熔断/反弹/突破/调整/抄底/补仓/解套/震荡/牛熊/支撑/压力位/平仓/换手/回踩/回调）
5. 必须包含至少 1 个命理术语（轻量点缀，不要长篇）：戊辰流年/比劫/印星/食伤/财官/大运/喜用神 之一即可
6. 末尾收尾语必须使用用户指定的关键词开头（用户会给你 5 个备选之一），格式：「{关键词}：xxx」，约 20-30 字
7. 不要分点、不要标题、不要 Markdown、不要表情列表
8. 不要"各位投资者""各位听众""各位观众朋友们"这种装腔开场
9. 禁词：死、亡、凶、灾、厄、寿终、大限、夭折（用"调整/转折/熔断/触底"代替）
10. 一段连贯文字，不要换行不要分段
"""


def _financial_term_for_kind(kind: str) -> str:
    """给三个高光年份提供风格暗示的金融术语。"""
    return {
        "high": "放量突破",
        "low": "触发熔断",
        "turn": "急速变盘",
    }.get(kind, "调整")


def _find_dayun_for_age(dayun_list: list[dict], age: int) -> str:
    """找到指定年龄所属大运的干支。"""
    for d in dayun_list:
        if d["start_age"] <= age <= d["end_age"]:
            return d["ganzhi"]
    return ""


def _find_liunian_gz(yearly_raw: list[dict] | None, year: int) -> str:
    """从 yearly_raw 找指定年的流年干支。"""
    if not yearly_raw:
        return ""
    for r in yearly_raw:
        if r.get("year") == year:
            return r.get("liunian_gz") or r.get("ganzhi") or ""
    return ""


def build_user_prompt(
    chart: dict,
    kline: list[dict],
    personality: dict,
    highlights: dict,
    yearly_raw: list[dict] | None = None,
    ending_keyword: str | None = None,
) -> str:
    """组装 user prompt。

    参数:
        chart: pipeline['chart']
        kline: 100 根 K 线
        personality: detect_personality 输出 {id,name,emoji,tagline}
        highlights: extract_highlight_years 输出 {high,low,turn}
        yearly_raw: pipeline['yearly_raw']（可选，用于查流年干支）
        ending_keyword: 指定收尾词；None 时随机轮换 ENDING_STYLES
    """
    if ending_keyword is None:
        ending_keyword = _pick_ending(personality, highlights)

    fp = chart["four_pillars"]
    closes = [k["close"] for k in kline]
    start_close = round(closes[0], 1)
    end_close = round(closes[-1], 1)
    avg_close = round(sum(closes) / len(closes), 1)

    red = sum(1 for k in kline if k["color"] == "red")
    green = sum(1 for k in kline if k["color"] == "green")

    dayun_list = chart.get("dayun", [])

    def _hl_line(kind: str) -> str:
        h = highlights.get(kind, {})
        if not h:
            return ""
        age = h.get("age", "?")
        year = h.get("year", "?")
        close = round(h.get("close", 0), 1)
        liunian_gz = _find_liunian_gz(yearly_raw, year)
        dayun_gz = _find_dayun_for_age(dayun_list, age) if isinstance(age, int) else ""
        kind_zh = {"high": "最高峰", "low": "最低谷", "turn": "最大转折"}[kind]
        suffix = []
        if liunian_gz:
            suffix.append(f"流年{liunian_gz}")
        if dayun_gz:
            suffix.append(f"{dayun_gz}大运")
        suffix_str = "（" + "、".join(suffix) + "）" if suffix else ""
        return f"  - {kind_zh}：{age} 岁（{year}年）close={close}{suffix_str}"

    highlight_lines = "\n".join(filter(None, [_hl_line("high"), _hl_line("low"), _hl_line("turn")]))

    return f"""请为以下命主写一段 90-120 字的命运 K 线短评（不能少于 90 字，不能多于 120 字）。

【标签】{personality['emoji']} {personality['name']}
【画像】{personality['tagline']}

【八字】{fp['year']} {fp['month']} {fp['day']} {fp['hour']}（日主{chart['day_master']}，{chart.get('strength', 'balanced')}）

【3 个高光年份】（必须把这 3 个年龄编进去）
{highlight_lines}

【全程数据】
起步 close = {start_close}
百岁 close = {end_close}
全程平均 = {avg_close}
红 K（上行）{red} 根 / 绿 K（下行）{green} 根

【收尾词】本次必须使用「{ending_keyword}：xxx」格式收尾，约 20-30 字，要俏皮反差，不要换其他关键词。

请严格遵守 system prompt 的硬约束，开头必须是"{personality['emoji']} {personality['name']}：".
"""


def build_messages(
    chart: dict,
    kline: list[dict],
    personality: dict,
    highlights: dict,
    yearly_raw: list[dict] | None = None,
    ending_keyword: str | None = None,
) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_user_prompt(
                chart, kline, personality, highlights, yearly_raw, ending_keyword=ending_keyword,
            ),
        },
    ]
