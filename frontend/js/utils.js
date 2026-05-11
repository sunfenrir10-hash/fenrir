// 通用工具：sessionStorage 暂存表单和结果，跨页传递
const Store = {
  KEY_FORM: "mingk_form",
  KEY_RESULT: "mingk_result",

  saveForm(d) { sessionStorage.setItem(this.KEY_FORM, JSON.stringify(d)); },
  loadForm() {
    const s = sessionStorage.getItem(this.KEY_FORM);
    return s ? JSON.parse(s) : null;
  },
  saveResult(d) { sessionStorage.setItem(this.KEY_RESULT, JSON.stringify(d)); },
  loadResult() {
    const s = sessionStorage.getItem(this.KEY_RESULT);
    return s ? JSON.parse(s) : null;
  },
  clear() {
    sessionStorage.removeItem(this.KEY_FORM);
    sessionStorage.removeItem(this.KEY_RESULT);
  },
};

function showToast(msg, ms = 2400) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), ms);
}

const STRENGTH_LABEL = {
  strong:   "身旺",
  balanced: "平衡",
  weak:     "身弱",
};

window.Store = Store;
window.showToast = showToast;
window.STRENGTH_LABEL = STRENGTH_LABEL;

// 顶部 ticker + topbar 注入（保持每页样板一致）
function renderHeader(rightHtml = "") {
  const tickerItems = [
    { code: "命运指数", price: "+82.40", change: "+1.62%", up: true },
    { code: "运势贝塔", price: "1.187",  change: "+0.04",   up: true },
    { code: "比劫率",   price: "0.42",   change: "-0.03",   up: false },
    { code: "财官分",   price: "67.10",  change: "+2.10",   up: true },
    { code: "大运σ",    price: "12.84",  change: "-0.55",   up: false },
    { code: "印星浓度", price: "0.31",   change: "+0.01",   up: true },
    { code: "食伤动量", price: "44.82",  change: "+3.40",   up: true },
    { code: "七杀压力", price: "21.05",  change: "-1.20",   up: false },
  ];
  const tickerHtml = tickerItems
    .concat(tickerItems) // 加倍便于无缝
    .map((it) => `
      <span class="ticker__item">
        <b>${it.code}</b>
        <span>${it.price}</span>
        <span class="${it.up ? "up" : "down"}">${it.change}</span>
      </span>`)
    .join("");

  const today = new Date();
  const dateStr = `${today.getFullYear()}.${String(today.getMonth() + 1).padStart(2,"0")}.${String(today.getDate()).padStart(2,"0")}`;

  const html = `
<div class="ticker">
  <div class="ticker__track">${tickerHtml}</div>
</div>
<div class="topbar">
  <a class="topbar__brand" href="index.html"><span class="dot"></span>MINGK · 命数终端</a>
  <div class="topbar__meta">
    <span>SESSION <b>${Math.random().toString(36).slice(2,8).toUpperCase()}</b></span>
    <span>DATE <b>${dateStr}</b></span>
    <span>STATUS <b style="color:var(--up)">LIVE</b></span>
  </div>
</div>`;

  const slot = document.getElementById("site-header");
  if (slot) slot.innerHTML = html;

  // 全局 footer（红线 P0：免责声明，文案不可改动一字）
  let footer = document.getElementById("site-footer");
  if (!footer) {
    footer = document.createElement("footer");
    footer.id = "site-footer";
    document.body.appendChild(footer);
  }
  footer.className = "disclaimer";
  footer.innerHTML = `<span class="text">仅供娱乐 切勿当真，大家都有很精彩的人生！</span><span class="dot"></span><span>MINGK · v0.4</span>`;
}

window.renderHeader = renderHeader;
