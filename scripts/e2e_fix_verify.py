"""Phase 4-2 修复验证截图：landing 12 人格 + form 纯 text + result fallback hint。"""

import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path("/Users/suncanyang/Desktop/mingk")
OUT = ROOT / "frontend/assets/screenshots/phase4-2-fix"
OUT.mkdir(parents=True, exist_ok=True)


def shoot_landing_form(page, prefix):
    # ① landing — 12 人格
    page.goto("http://127.0.0.1:8001/index.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)
    cards = page.locator(".sample-card").count()
    print(f"[{prefix}] landing sample-card count={cards}")
    page.screenshot(path=str(OUT / f"{prefix}_01_landing.png"), full_page=True)

    # ② form — 纯 text input，敲一个非列表城市
    page.goto("http://127.0.0.1:8001/form.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    has_datalist = page.locator("datalist#city-list").count()
    print(f"[{prefix}] form datalist count={has_datalist} (expect 0)")
    page.fill("#birth_date", "1991-05-12")
    page.fill("#birth_time", "08:00")
    page.fill("#city", "怀化")
    page.screenshot(path=str(OUT / f"{prefix}_02_form_huaihua.png"), full_page=True)


def shoot_fallback_result(page, prefix, city_input, name):
    """填一个识别不了的城市，跑一遍流程，截 result fallback hint。"""
    page.goto("http://127.0.0.1:8001/form.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    page.fill("#birth_date", "1991-05-12")
    page.fill("#birth_time", "08:00")
    # 用 evaluate 直接清空再填
    page.eval_on_selector("#city", "el => el.value = ''")
    page.fill("#city", city_input)
    page.click("button[type=submit]")
    # waiting 9.7s 动画 + API
    page.wait_for_url("**/result.html", timeout=20000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)  # ECharts
    notice_text = page.locator("#city-notice").inner_text()
    notice_class = page.locator("#city-notice").get_attribute("class")
    print(f"[{prefix}/{name}] notice='{notice_text[:80]}' class={notice_class}")
    page.screenshot(path=str(OUT / f"{prefix}_03_result_{name}.png"), full_page=True)


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for vp_name, w, h in [("desktop", 1440, 900), ("mobile", 390, 844)]:
                ctx = browser.new_context(viewport={"width": w, "height": h})
                page = ctx.new_page()
                shoot_landing_form(page, vp_name)
                shoot_fallback_result(page, vp_name, "瞎敲abcdef", "fallback")
                shoot_fallback_result(page, vp_name, "怀化", "huaihua")
                ctx.close()
        finally:
            browser.close()
    print("\nDone. Screenshots in:", OUT)
    for p in sorted(OUT.glob("*.png")):
        print(" -", p.name, p.stat().st_size, "B")


if __name__ == "__main__":
    main()
