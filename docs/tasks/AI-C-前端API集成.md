# AI-C 任务：前端真实 API 集成

## 目标
把 `web/app.js` 里的 mock 逻辑改成真实 fetch，对接服务端 API，让 demo 能跑通"说话 → 出谱 → 记忆增长"的完整闭环。

## 背景
项目里已有：
- `web/index.html`：三栏布局（对话/谱面/记忆）
- `web/app.js`：目前用 mock 数据，需要改成真实 API 调用
- `web/style.css`：样式完整，不用动
- `server.py`：FastAPI 服务端，目前也是 mock，我（主 AI）正在改成真实集成

**重要**：alphaTab 的正确用法我刚修复过，直接参考下面"alphaTab 集成"部分的代码。

## API 契约（服务端最终格式）

### POST /api/chat
请求：
```json
{ "message": "我想弹 God Knows" }
```
响应：
```json
{
  "reply": "已为你生成《God Knows》的吉他谱，根据你的能力画像做了以下改编：...",
  "alphatex": "\\title \"God Knows\" \\tempo 120 . 0.3.4 2.3.4 | ..."
}
```

### GET /api/memory
响应：
```json
{
  "profile": { "level": "中级", "no_barre": true, "fav_genre": "ACG" },
  "rules": [
    { "id": 1, "text": "弹不了十六分音符", "hit_count": 3, "created_at": "..." }
  ],
  "episodes_count": 2,
  "cost": {
    "total_tokens_in": 1234,
    "total_tokens_out": 567,
    "total_latency_ms": 890.5,
    "memory_ops": 15,
    "memory_count": 6
  }
}
```

## 需要改动的功能

### 1. 对话发送（`/api/chat`）
- 用户输入 → POST → 收到 `reply` + `alphatex`
- `reply` 显示在对话区
- `alphatex` 传给 alphaTab 渲染

### 2. alphaTab 渲染（关键，刚修复过）
```javascript
function renderScore(alphaTex) {
    scoreContainer.innerHTML = '';
    const apiDiv = document.createElement('div');
    apiDiv.id = 'alphaTab-api';
    apiDiv.style.width = '100%';
    scoreContainer.appendChild(apiDiv);

    alphaTabApi = new alphaTab.AlphaTabApi(apiDiv, {
        core: { tex: true },  // 关键：tex: true，不是传字符串
        display: {
            layoutMode: alphaTab.LayoutMode.Page,
            staveProfile: alphaTab.StaveProfile.ScoreTab,
            barCountPerPartial: 4,
        },
        player: {
            enablePlayer: true,
            enableCursor: true,
            enableAnimatedBeatCursor: true,
            enableUserInteraction: true,
        },
        notation: {
            elements: { chordDiagrams: false },
        },
    });
    alphaTabApi.tex(alphaTex);  // 关键：通过 api.tex() 传内容

    // 播放控制
    playBtn.onclick = () => { if (alphaTabApi) alphaTabApi.playPause(); };
    stopBtn.onclick = () => { if (alphaTabApi) alphaTabApi.stop(); };
}
```

**常见错误**（已踩过坑）：
- ❌ `core: { tex: alphaTexString }` — 这是错的，alphaTab 不会解析
- ❌ JS 模板字符串里写 `\title` — `\t` 会被转义成 tab
- ✅ 正确：`core: { tex: true }` + `api.tex(alphaTexString)`

### 3. 记忆面板轮询（`/api/memory`）
- 每 2 秒 GET `/api/memory`
- 画像：键值对显示
- 规则：列表显示，新增规则高亮（已有逻辑保留）
- 成本统计：显示 token/延迟/记忆条数

### 4. 播放/停止按钮
- 播放：`api.playPause()`
- 停止：`api.stop()`

## 验收标准
1. 启动服务端 `python server.py`
2. 浏览器打开 `http://localhost:8000`
3. 发送消息"我想弹 God Knows"：
   - 对话区显示 Agent 回复
   - 谱面区渲染出吉他谱（五线谱 + TAB）
   - 记忆面板显示画像/规则/成本
4. 再发一条"这段太快了"，记忆面板规则数 +1

## 文件位置
- 修改 `web/app.js`（主要工作）
- 如需要可微调 `web/index.html`（不建议大改）

## 提示
- 先读现有的 `web/app.js` 了解结构
- 用 `fetch` 或 `XMLHttpRequest` 都行，项目没引 axios
- 如果服务端还没好，可以先写代码，用 mock 数据自测
- alphaTab CDN：`https://cdn.jsdelivr.net/npm/@coderline/alphatab@latest/dist/alphaTab.js`
