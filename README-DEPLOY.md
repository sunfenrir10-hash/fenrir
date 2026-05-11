# Mingk · 部署指南（Vercel 全栈）

预计耗时：**10-15 分钟**。这份指南把部署拆成 3 步，每一步都给具体命令和点击路径。

---

## 一、推到 GitHub（3 分钟）

### 1.1 建一个仓库

1. 打开 [github.com/new](https://github.com/new)
2. **Repository name**：`mingk`
3. **Private** 勾上（你愿意 public 也行）
4. 不要勾 README / .gitignore / license（本地已有）
5. 点 **Create repository**

### 1.2 本地 push

把下面 `<你的用户名>` 替换成你的 GitHub 账号名，然后在终端跑：

```bash
cd /Users/suncanyang/Desktop/mingk
git add -A
git commit -m "Phase 5: ready to deploy"
git remote add origin https://github.com/<你的用户名>/mingk.git
git branch -M main
git push -u origin main
```

如果之前已经 add 过 remote 报 `remote origin already exists`，跑：
```bash
git remote set-url origin https://github.com/<你的用户名>/mingk.git
git push -u origin main
```

push 完刷新 GitHub 网页，能看到全部代码就 OK。

---

## 二、Vercel 部署（5 分钟）

### 2.1 注册 / 登录

1. 打开 [vercel.com](https://vercel.com)
2. 点右上角 **Sign Up** → 选 **Continue with GitHub**（最省事）
3. 授权 Vercel 访问你的 GitHub

### 2.2 Import 仓库

1. 登录后进 dashboard，点 **Add New** → **Project**
2. 找到 `mingk` 仓库 → 点 **Import**
3. **Framework Preset** 会自动识别为 `Other`，**保持默认**
4. **Root Directory** 默认 `.`，**保持默认**
5. 不要点 Deploy！先做下一步

### 2.3 加环境变量

在 Import 页面下方展开 **Environment Variables**：

| Name | Value |
|---|---|
| `KIMI_API_KEY` | 你的 Moonshot API Key（[在这里申请](https://platform.moonshot.cn/console/api-keys)） |

加完点 **Deploy**。

### 2.4 等部署完成

- 第一次部署需要装依赖（lunar-python / openai / slowapi），约 2-3 分钟
- 完成后会跳到 dashboard，显示 **Visit** 按钮和你的域名 `https://mingk-xxx.vercel.app`

> 如果 build 失败，看红字 log。常见原因：
> - `requirements.txt` 装包超时 → 重新 Deploy 一般能过
> - `KIMI_API_KEY` 没填 → 加上后 redeploy

---

## 三、烟雾测试（3 分钟）

打开你的部署 URL `https://mingk-xxx.vercel.app`，按下面清单挨个验：

- [ ] **Landing 页**：黑底加载正常，能看到 12 个人格卡，"开始排盘" 按钮可点
- [ ] **表单页**：填 `1991-05-12` / `08:00` / `北京` / `女` / 标题随便 → 点提交
- [ ] **等待页**：4 阶段动画跑 8-10s
- [ ] **结果页**：K 线 + narrative + 标签徽章（emoji）正常
- [ ] **分享卡**：点 "保存为图片" → 能下载 PNG（含免责声明 + 二维码）

任何一步失败，复制 **完整错误信息 + 浏览器 console 报错截图** 发给 manager。

---

## 四、（可选）改 OG meta 里的 URL

部署完拿到真实 URL 后，建议把 5 个 HTML 里的 OG meta 占位 URL 改成你的真实域名。

```bash
cd /Users/suncanyang/Desktop/mingk
# 把所有 mingk.vercel.app 替换成你的真实域名（举例 mingk-abc123.vercel.app）
find frontend -name '*.html' -exec sed -i '' 's|https://mingk.vercel.app|https://mingk-abc123.vercel.app|g' {} +
find frontend -name '*.xml' -exec sed -i '' 's|https://mingk.vercel.app|https://mingk-abc123.vercel.app|g' {} +
find frontend -name 'robots.txt' -exec sed -i '' 's|https://mingk.vercel.app|https://mingk-abc123.vercel.app|g' {} +
git add -A && git commit -m "Update OG URLs to production domain" && git push
```

Vercel 会自动 redeploy。

---

## 五、（可选）绑定 mingk.com 域名

冲量数据看完再决定要不要买。流程：

1. 在 [Cloudflare Registrar](https://dash.cloudflare.com/) 注册 `mingk.com`（约 $10/年，最便宜）
2. Vercel project → **Settings** → **Domains** → **Add** → 输 `mingk.com`
3. Vercel 会给你 2 条 DNS 记录，复制到 Cloudflare DNS
4. 等 DNS 生效（通常 5-30 分钟），HTTPS 自动配好

---

## 排错速查

**问题：vercel build 报 `Module not found: lunar-python`**
- 检查 `requirements.txt` 是否包含 `lunar-python>=1.4.4`

**问题：调 /api/chart 返回 500**
- 进 Vercel project → **Logs** 看实时日志
- 多半是 `KIMI_API_KEY` 没设或 quota 用完

**问题：429 Too Many Requests**
- 同一 IP 1 分钟内调超过 5 次 chart，等 1 分钟即可
- 想关闭限流：环境变量加 `MINGK_RATELIMIT=0` 然后 redeploy

**问题：Chart 一直 loading 不出来**
- Vercel 函数超时默认 60s（已配置在 `vercel.json`），lunar-python 排盘 + LLM 一般 5-15s
- 如果首次冷启动慢，刷新一次再试

---

## 当前已完成清单

- ✅ Phase 1-4: 算法 / 旺衰 / LLM / 12 人格 / 5 页前端 / 9:16 分享卡 / 387 城 / 免责声明 / 移动适配 / 5 命盘 QA
- ✅ Phase 5: Vercel 函数入口 / vercel.json / 速率限制 / OG meta / robots & sitemap

**80+ 单元测试全过**。准备就绪，开冲。
