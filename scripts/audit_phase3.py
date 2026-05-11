"""Phase 3.5 Step 3.5-3: 10 命盘短卡抽检（120 字 + 标签 + 段子手风）。"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from datetime import datetime

from src.pipeline import pipeline
from src.llm import call_llm, is_mock_mode
from src.narrative_sanitize import has_blacklist_word, BLACKLIST_REPLACEMENTS, sanitize_narrative, truncate_to_limit
from src.personality import detect_personality, extract_highlight_years
from src.prompt import ENDING_STYLES


CASES: list[tuple[str, tuple]] = [
    ("乔布斯",   (1955, 2, 24, 19, 15, "旧金山", 1)),
    ("马斯克",   (1971, 6, 28, 7,  30, "比勒陀利亚", 1)),
    ("巴菲特",   (1930, 8, 30, 15, 0,  "奥马哈", 1)),
    ("1991北京",  (1991, 5, 12, 8,  0,  "北京", 1)),
    ("F1_1968广州女", (1968, 11, 3,  4,  20, "广州", 0)),
    ("F2_1980成都男", (1980, 3,  17, 23, 45, "成都", 1)),
    ("F3_1995上海女", (1995, 7,  9,  12, 0,  "上海", 0)),
    ("F4_2003杭州男", (2003, 1,  28, 16, 50, "杭州", 1)),
    ("F5_1947西安女", (1947, 9,  21, 6,  10, "西安", 0)),
    ("F6_2010东京男", (2010, 12, 14, 21, 30, "东京", 1)),
]

FINANCIAL_TERMS = [
    "放量", "涨停", "熔断", "反弹", "突破", "调整", "抄底", "补仓",
    "解套", "震荡", "牛", "熊", "支撑", "压力位", "平仓", "换手",
    "回踩", "回调", "新高", "新低", "K 线", "K线", "走势", "上升通道",
    "底部", "顶部", "盘整", "横盘", "止损", "止盈", "高位", "低位",
]


def count_chinese_chars(text: str) -> int:
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')


def count_age_mentions(text: str) -> int:
    """匹配类似 '28 岁' / '47岁' / '70 岁'。"""
    return len(re.findall(r"\d+\s*岁", text))


def count_financial_terms(text: str) -> tuple[int, list[str]]:
    hits = [t for t in FINANCIAL_TERMS if t in text]
    return len(hits), hits


def has_markdown(text: str) -> tuple[bool, list[str]]:
    issues = []
    if re.search(r"^#{1,6}\s", text, re.M):
        issues.append("heading(#)")
    if re.search(r"\*\*[^*]+\*\*", text):
        issues.append("bold(**)")
    if re.search(r"^[-*]\s", text, re.M):
        issues.append("bullet")
    if re.search(r"^\d+\.\s", text, re.M):
        issues.append("ordered_list")
    if "```" in text:
        issues.append("code_fence")
    return (len(issues) > 0), issues


def find_blacklist_hits(text: str) -> list[str]:
    return [bad for bad, _ in BLACKLIST_REPLACEMENTS if bad in text]


def main() -> int:
    if is_mock_mode():
        print("[ERROR] KIMI_API_KEY 未设置")
        return 1
    print(f"[OK] KIMI_API_KEY 已设置（长度 {len(os.environ['KIMI_API_KEY'])}）")

    results: list[dict] = []
    t0 = time.time()
    total_out_chars = 0
    tag_counts: dict[str, int] = {}

    for name, args in CASES:
        print(f"\n=== {name} {args} ===", flush=True)
        try:
            r = pipeline(*args)
        except Exception as e:
            print(f"  pipeline 失败: {e}")
            results.append({"name": name, "error": f"pipeline: {e}"})
            continue

        personality = detect_personality(r["kline"])
        highlights = extract_highlight_years(r["kline"])
        tag_counts[personality["name"]] = tag_counts.get(personality["name"], 0) + 1

        try:
            t_call = time.time()
            raw = call_llm(
                r["chart"], r["kline"],
                personality=personality,
                highlights=highlights,
                yearly_raw=r["yearly_raw"],
                sanitize=False,
            )
            elapsed = time.time() - t_call
        except Exception as e:
            print(f"  LLM 调用失败: {e}")
            results.append({"name": name, "error": f"llm: {e}"})
            return 2

        filtered = sanitize_narrative(raw)
        truncated = truncate_to_limit(filtered, limit=120, hard_max=130)

        cn = count_chinese_chars(truncated)
        n_fin, fin_hits = count_financial_terms(truncated)
        md_bad, md_issues = has_markdown(truncated)
        bl_filtered = find_blacklist_hits(truncated)
        age_n = count_age_mentions(truncated)
        starts_with_tag = truncated.startswith(personality["emoji"])
        contains_tag_name = personality["name"] in truncated
        # 命中结尾词（找最后 30 字内出现哪个 ENDING_STYLES，空格无关比对）
        # 同时接受 LLM 常见近义变体（"一句点评" ≈ "一句话点评" 等）
        tail = truncated[-40:].replace(" ", "")
        ending_aliases = {
            "评级": ["评级"],
            "K 线总结": ["K线总结", "K线"],
            "今日操作建议": ["今日操作建议", "操作建议"],
            "一句话点评": ["一句话点评", "一句点评"],
            "买点提示": ["买点提示", "买点"],
        }
        ending_hit = None
        for canonical, aliases in ending_aliases.items():
            if any(a.replace(" ", "") in tail for a in aliases):
                ending_hit = canonical
                break

        record = {
            "name": name,
            "args": list(args),
            "bazi": list(r["chart"]["four_pillars"].values()),
            "strength": r["chart"]["strength"],
            "personality": personality,
            "highlights": highlights,
            "filtered_length_cn": cn,
            "raw_length_cn": count_chinese_chars(raw),
            "age_mention_count": age_n,
            "starts_with_tag_emoji": starts_with_tag,
            "contains_tag_name": contains_tag_name,
            "financial_term_count": n_fin,
            "financial_terms": fin_hits,
            "markdown_issues": md_issues,
            "blacklist_in_filtered": bl_filtered,
            "ending_keyword": ending_hit,
            "elapsed_sec": round(elapsed, 2),
            "narrative_raw": raw,
            "narrative_filtered": truncated,
        }
        results.append(record)
        total_out_chars += len(raw)
        print(f"  标签={personality['emoji']}{personality['name']} 旺衰={record['strength']}")
        print(f"  字数(中)={cn}(raw={record['raw_length_cn']}) 年龄={age_n} 金融={n_fin}({fin_hits[:3]}) "
              f"开头emoji={starts_with_tag} 黑名单={len(bl_filtered)} 结尾={ending_hit} 耗时={elapsed:.1f}s")
        print(f"  → {truncated}")

    elapsed_total = time.time() - t0

    valid = [r for r in results if "error" not in r]
    n = max(len(valid), 1)
    ending_counts: dict[str, int] = {}
    for r in valid:
        ek = r.get("ending_keyword") or "(无)"
        ending_counts[ek] = ending_counts.get(ek, 0) + 1
    max_tag_share = max(tag_counts.values()) / n * 100 if tag_counts else 0
    summary = {
        "total_cases": len(CASES),
        "succeeded": len(valid),
        "failed": len(CASES) - len(valid),
        "length_le_120_pct": sum(1 for r in valid if r["filtered_length_cn"] <= 120) / n * 100,
        "length_le_130_pct": sum(1 for r in valid if r["filtered_length_cn"] <= 130) / n * 100,
        "starts_with_tag_pct": sum(1 for r in valid if r["starts_with_tag_emoji"]) / n * 100,
        "contains_tag_name_pct": sum(1 for r in valid if r["contains_tag_name"]) / n * 100,
        "ge2_age_mentions_pct": sum(1 for r in valid if r["age_mention_count"] >= 2) / n * 100,
        "ge2_financial_terms_pct": sum(1 for r in valid if r["financial_term_count"] >= 2) / n * 100,
        "no_blacklist_pct": sum(1 for r in valid if not r["blacklist_in_filtered"]) / n * 100,
        "no_markdown_pct": sum(1 for r in valid if not r["markdown_issues"]) / n * 100,
        "avg_length_cn": round(statistics.mean(r["filtered_length_cn"] for r in valid), 1) if valid else 0,
        "avg_financial_terms": round(statistics.mean(r["financial_term_count"] for r in valid), 2) if valid else 0,
        "tag_distribution": tag_counts,
        "unique_tags": len(tag_counts),
        "max_single_tag_share_pct": round(max_tag_share, 1),
        "ending_distribution": ending_counts,
        "unique_endings": len([k for k in ending_counts if k != "(无)"]),
        "total_elapsed_sec": round(elapsed_total, 2),
        "total_output_chars": total_out_chars,
    }

    output = {"summary": summary, "cases": results, "timestamp": datetime.now().isoformat()}
    out_path = f"phase3_audit_{int(time.time())}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n详细结果写入: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
