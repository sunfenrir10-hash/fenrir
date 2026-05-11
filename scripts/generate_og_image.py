"""生成 og-image.png（1200×630）— 用 Playwright 渲染 HTML 模板截图。

设计：
- 黑底 #0a0a0a + 红色 K 线 accent
- 大字 "人生K线" + slogan "你是哪一只"
- 12 人格 emoji 横排
- 右下角 mingk.vercel.app
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path("/Users/suncanyang/Desktop/mingk")
OUT = ROOT / "frontend/og-image.png"

HTML = """
<!doctype html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Noto+Serif+SC:wght@900&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { width: 1200px; height: 630px; overflow: hidden; }
  body {
    background: #0a0a0a;
    font-family: 'JetBrains Mono', monospace;
    color: #e8e8ec;
    position: relative;
    background-image:
      linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
  }
  .topbar {
    position: absolute; top: 0; left: 0; right: 0; height: 56px;
    border-bottom: 1px solid #20202a;
    display: flex; align-items: center; padding: 0 40px;
    font-size: 13px; letter-spacing: 0.18em; color: #6e6e7a;
  }
  .topbar b { color: #ef3b3b; font-weight: 800; margin-right: 14px; }
  .stage {
    position: absolute; top: 56px; left: 0; right: 0; bottom: 0;
    padding: 60px 70px;
    display: flex; flex-direction: column;
  }
  .tag {
    font-size: 14px; letter-spacing: 0.32em; color: #ef3b3b;
    margin-bottom: 18px; font-weight: 700;
  }
  h1 {
    font-family: 'Noto Serif SC', serif; font-weight: 900;
    font-size: 130px; line-height: 1; color: #ffffff;
    letter-spacing: -0.02em;
  }
  h1 .accent { color: #ef3b3b; }
  .slogan {
    font-family: 'Noto Serif SC', serif; font-weight: 900;
    font-size: 62px; color: #e8e8ec; margin-top: 22px;
    letter-spacing: 0.04em;
  }
  .slogan .green { color: #2cba5f; }
  .emojis {
    margin-top: 48px;
    display: flex; gap: 20px; align-items: center;
    font-size: 38px;
    filter: drop-shadow(0 2px 8px rgba(239,59,59,0.25));
  }
  .footer {
    position: absolute; bottom: 32px; left: 70px; right: 70px;
    display: flex; justify-content: space-between; align-items: flex-end;
    font-size: 13px; letter-spacing: 0.2em; color: #9a9aa6;
  }
  .url { color: #ffffff; font-weight: 700; font-size: 18px; letter-spacing: 0.18em; }
  .kline {
    position: absolute; right: 70px; top: 110px;
    display: flex; gap: 6px; align-items: flex-end; height: 220px;
  }
  .kline .b {
    width: 14px; background: #ef3b3b;
  }
  .kline .b.g { background: #2cba5f; }
</style>
</head>
<body>
  <div class="topbar"><b>MINGK</b><span>/ 命运指数 +47.83% · 比劫率 0.62 · 食伤动量 ↑↑ · LLM ENGINE LOCKED</span></div>

  <div class="kline">
    <div class="b" style="height:60%"></div>
    <div class="b g" style="height:42%"></div>
    <div class="b" style="height:78%"></div>
    <div class="b" style="height:55%"></div>
    <div class="b g" style="height:30%"></div>
    <div class="b" style="height:88%"></div>
    <div class="b" style="height:68%"></div>
    <div class="b g" style="height:48%"></div>
    <div class="b" style="height:72%"></div>
    <div class="b" style="height:90%"></div>
    <div class="b g" style="height:36%"></div>
    <div class="b" style="height:64%"></div>
  </div>

  <div class="stage">
    <div class="tag">/ LIFE&nbsp;K-LINE&nbsp;CHART · 命运回测</div>
    <h1>人生<span class="accent">K线图</span></h1>
    <div class="slogan">看看你是<span class="green">哪一只</span></div>
    <div class="emojis">👑 🐂 🚀 💊 🦋 🔄 🎢 🌅 🎩 🐢 🏛️ 💎</div>
  </div>

  <div class="footer">
    <span>仅供娱乐 切勿当真，大家都有很精彩的人生！</span>
    <span class="url">mingk.vercel.app</span>
  </div>
</body></html>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        page = ctx.new_page()
        page.set_content(HTML, wait_until="networkidle")
        page.wait_for_timeout(800)  # 等 webfont
        page.screenshot(path=str(OUT), full_page=False, omit_background=False, clip={"x": 0, "y": 0, "width": 1200, "height": 630})
        browser.close()
    print("Wrote", OUT, OUT.stat().st_size, "B")


if __name__ == "__main__":
    main()
