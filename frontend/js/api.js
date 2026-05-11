// 后端 API 封装
// 生产环境使用相对路径（同域），本地开发可手动设 window.MINGK_API_BASE = "http://127.0.0.1:8000"
window.MINGK_API_BASE = window.MINGK_API_BASE || "";

const API = {
  base: window.MINGK_API_BASE,

  async health() {
    const r = await fetch(`${this.base}/healthz`);
    if (!r.ok) throw new Error(`healthz ${r.status}`);
    return r.json();
  },

  async cities() {
    const r = await fetch(`${this.base}/api/cities`);
    if (!r.ok) throw new Error(`cities ${r.status}`);
    const d = await r.json();
    return d.cities || [];
  },

  async personalities() {
    const r = await fetch(`${this.base}/api/personalities`);
    if (!r.ok) throw new Error(`personalities ${r.status}`);
    return r.json();
  },

  async chart(payload) {
    const r = await fetch(`${this.base}/api/chart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      let msg;
      try { msg = (await r.json()).detail || `HTTP ${r.status}`; }
      catch { msg = `HTTP ${r.status}`; }
      throw new Error(msg);
    }
    return r.json();
  },
};

window.API = API;
