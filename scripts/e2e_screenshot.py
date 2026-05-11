"""端到端联调 + 截图脚本 Phase 4-2。

流程：landing → form → waiting(3帧) → result → share
每命盘在 desktop(1440×900) 和 mobile(390×844) 下各截图。
输出: frontend/assets/screenshots/phase4-2/{name}/0X_{stage}_{viewport}.png
"""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8001"
OUT_ROOT = Path("/Users/suncanyang/Desktop/mingk/frontend/assets/screenshots/phase4-2")

CHARTS = [
    {"name": "jobs",    "birth_date": "1955-02-24", "birth_time": "19:15", "city": "旧金山",     "gender": 1, "title": "乔布斯"},
    {"name": "musk",    "birth_date": "1971-06-28", "birth_time": "07:30", "city": "比勒陀利亚", "gender": 1, "title": "马斯克"},
    {"name": "buffett", "birth_date": "1930-08-30", "birth_time": "15:00", "city": "奥马哈",     "gender": 1, "title": "巴菲特"},
    {"name": "bj91",    "birth_date": "1991-05-12", "birth_time": "08:00", "city": "北京",       "gender": 0, "title": "北京1991女"},
    {"name": "sh00",    "birth_date": "2000-01-01", "birth_time": "00:00", "city": "上海",       "gender": 0, "title": "上海2000女"},
]

VIEWPORTS = [
    {"label": "desktop", "width": 1440, "height": 900},
    {"label": "mobile",  "width": 390,  "height": 844},
]


def shoot(page, out_dir: Path, filename: str, full=True):
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / filename
    page.screenshot(path=str(p), full_page=full)
    print(f"  saved {p.relative_to(Path('/Users/suncanyang/Desktop/mingk'))}")
    return str(p)


def run_chart(playwright_obj, chart: dict, viewport_cfg: dict) -> list[str]:
    """Run one chart × one viewport. Returns list of saved paths."""
    label = viewport_cfg["label"]
    vp = {"width": viewport_cfg["width"], "height": viewport_cfg["height"]}
    out_dir = OUT_ROOT / chart["name"]
    saved = []

    browser = playwright_obj.chromium.launch(headless=True)
    context = browser.new_context(viewport=vp, device_scale_factor=2)
    page = context.new_page()
    print(f"\n  [{chart['name']}] {label} {vp['width']}x{vp['height']}")

    try:
        # --- 清除 sessionStorage / localStorage ---
        page.goto("about:blank")

        # 1. Landing
        page.goto(BASE + "/index.html", wait_until="domcontentloaded")
        page.wait_for_selector(".hero__title", timeout=8000)
        page.wait_for_timeout(500)
        saved.append(shoot(page, out_dir, f"01_landing_{label}.png"))

        # 2. Form
        page.click('.hero__cta a.btn[href="form.html"]')
        page.wait_for_selector("#chart-form", timeout=8000)
        # 等城市 datalist 加载完毕
        page.wait_for_function(
            "document.querySelectorAll('#city-list option').length > 5",
            timeout=10000,
        )

        page.fill("#birth_date", chart["birth_date"])
        page.fill("#birth_time", chart["birth_time"])
        # 城市用 fill（input + datalist，不是 select）
        page.fill("#city", chart["city"])
        page.wait_for_timeout(400)

        # 性别 radio
        gender_val = str(chart["gender"])
        page.evaluate(
            f"""() => {{
                const r = document.querySelector('input[name=gender][value="{gender_val}"]');
                if (r) r.click();
            }}"""
        )

        # title
        if chart.get("title"):
            page.fill("#title", chart["title"])

        page.wait_for_timeout(300)
        saved.append(shoot(page, out_dir, f"02_form_{label}.png"))

        # 3. Submit -> Waiting
        page.click('button[type=submit]')
        page.wait_for_url("**/waiting.html", timeout=8000)
        page.wait_for_selector(".ritual", timeout=5000)

        # 3a: 第 1.5s 帧
        page.wait_for_timeout(1500)
        saved.append(shoot(page, out_dir, f"03a_waiting_{label}.png"))

        # 3b: 第 4s 帧
        page.wait_for_timeout(2500)  # 累计 4s
        saved.append(shoot(page, out_dir, f"03b_waiting_{label}.png"))

        # 3c: 第 7s 帧
        page.wait_for_timeout(3000)  # 累计 7s
        saved.append(shoot(page, out_dir, f"03c_waiting_{label}.png"))

        # 4. Result - 给足够长的 timeout（waiting 约 9.7s，给 15s 余量）
        page.wait_for_url("**/result.html", timeout=15000)
        page.wait_for_selector("#chart", timeout=10000)
        page.wait_for_timeout(1500)  # 等图表动画
        saved.append(shoot(page, out_dir, f"04_result_{label}.png"))

        # 5. Share
        page.click("#btn-share")
        page.wait_for_url("**/share.html", timeout=8000)
        page.wait_for_selector("#sc-chart", timeout=10000)
        page.wait_for_timeout(1500)
        saved.append(shoot(page, out_dir, f"05_share_{label}.png"))

    except Exception as e:
        print(f"  ERROR [{chart['name']}][{label}]: {e}")
        # 保存失败截图供调试
        try:
            debug_path = out_dir / f"ERR_{label}_{int(time.time())}.png"
            page.screenshot(path=str(debug_path), full_page=True)
            print(f"  debug screenshot: {debug_path}")
        except Exception:
            pass
        raise
    finally:
        context.close()
        browser.close()

    return saved


def main():
    all_saved: list[str] = []
    failures: list[str] = []

    with sync_playwright() as p:
        for chart in CHARTS:
            for vp in VIEWPORTS:
                tag = f"{chart['name']}/{vp['label']}"
                try:
                    paths = run_chart(p, chart, vp)
                    all_saved.extend(paths)
                except Exception as e:
                    failures.append(f"{tag}: {e}")

    print("\n" + "=" * 60)
    print(f"DONE. {len(all_saved)} screenshots saved.")
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
    else:
        print("No failures.")
    print("=" * 60)

    # Print all saved paths
    print("\nAll saved paths:")
    for s in sorted(all_saved):
        print(f"  {s}")


if __name__ == "__main__":
    main()
