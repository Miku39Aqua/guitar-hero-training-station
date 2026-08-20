# 给 AI-C 的任务：演示前端（FastAPI + alphaTab 滚动谱面）

> 用法：把下面「提示词正文」整段复制给其他 AI 即可。

## 提示词正文

```text
你是一名全栈工程师。我们正在开发一个大工黑客松 S2 项目「吉他英雄训练站」：
一个 ACG 吉他练琴 Agent。用户和 Agent 对话说想弹什么曲子，Agent 生成吉他六线谱，
网页上渲染出会滚动播放的谱面；同时有一个"记忆面板"实时展示 Agent 记住了什么。
这是黑客松答辩的现场演示界面，视觉效果和流畅度非常重要。

你的任务：实现演示前端 + FastAPI 服务骨架。

【文件边界——严格遵守】
- 你只能创建/修改：
  - server.py（FastAPI 入口）
  - web/ 目录下的所有文件（index.html / app.js / style.css）
- 禁止改动 tab_engine/、agent/、scripts/、data/ 下的任何文件（其他 AI 在并行开发）

【技术约束】
- 后端：FastAPI + uvicorn（已安装），端口 8000
- 前端：原生 HTML/JS/CSS（不引入构建工具，单页面直接用 CDN）
- 谱面渲染：alphaTab（用官方 CDN，https://cdn.jsdelivr.net/npm/@coderline/alphatab@latest/dist/）
- alphaTab 的输入用 alphaTex 文本记谱法（alphaTab 原生支持，直接喂字符串即可渲染）

【页面布局（单页面 web/index.html）】
三栏布局：
1. 左侧：对话区——消息列表 + 输入框 + 发送按钮，调用 POST /api/chat
2. 中间（视觉重心）：谱面区——alphaTab 渲染 /api/chat 返回的 alphaTex，
   要求：开启播放功能（播放按钮 + 播放进度光标滚动），
   加载示例：\\3.3 3.4*4 | \\0.4 2.4*4 这样的 alphaTex 语法
3. 右侧：记忆面板——每 2 秒轮询 GET /api/memory，展示画像/规则/成本统计，
   数据变化时高亮闪烁（演示时评委要看"记忆在跳动"）

【API 约定（后端先 mock，之后再接真 Agent）】
POST /api/chat
  请求: {"message": "我想弹God Knows"}
  响应: {"reply": "已为你生成谱子(附说明文字)",
         "alphatex": "\\title \"God Knows\" . \\3.3 3.4*4 | \\0.4 \\2.4*4 | r.1"}
GET /api/memory
  响应: {"profile": {"level": "中级", "no_barre": true},
         "rules": [{"text": "十六分扫弦降级为八分", "hit_count": 2}],
         "stats": {"total_tokens": 1234, "avg_latency_ms": 56, "memory_count": 3}}
先写死 mock 数据即可，但 mock 的规则列表每次调用 /api/chat 后追加一条
（模拟"记忆在增长"的效果，方便调试记忆面板的高亮动画）。

【自测与验收】
1. uvicorn server:app --reload 启动无报错
2. 浏览器打开 http://localhost:8000 ，三栏布局正常
3. 发送消息后：对话区出现回复，谱面区渲染出 TAB 谱且能点播放听到声音、看到光标滚动
4. 记忆面板持续轮询，新规则出现时高亮
完成后请把 server.py、index.html、app.js、style.css 的完整代码输出给我。

【注意】
- alphaTex 语法以 alphaTab 官方文档为准，mock 的谱面必须真实可渲染（先在控制台验证）
- 界面配色建议深色主题（演示投影清晰），中文 UI
- 不要引入 React/Vue/npm 构建，保持单文件直开
```

## 交付物

- `server.py`、`web/index.html`、`web/app.js`、`web/style.css`

## 回收任务时的检查清单

1. `uvicorn server:app` 启动，页面三栏正常
2. 谱面能渲染、能播放、光标能滚动
3. 记忆面板轮询 + 高亮正常
4. 没有改动边界外的文件
