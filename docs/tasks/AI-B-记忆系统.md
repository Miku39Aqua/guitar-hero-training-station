# 给 AI-B 的任务：记忆系统（memory.py 实现）

> 用法：把下面「提示词正文」整段复制给其他 AI，并把项目里的 `agent/memory.py` 接口 stub 一并贴给它。

## 提示词正文

```text
你是一名资深 Python 工程师。我们正在开发一个大工黑客松 S2 项目「吉他英雄训练站」：
一个 ACG 吉他练琴 Agent。用户说想弹什么曲子，Agent 生成吉他谱和音色方案；
用户反馈后，系统要记住偏好，在后续相似任务中自动应用。这个项目投递的赛道之一是
「开发一个具备反馈记忆能力的轻量 Agent 系统」，考查点是：记忆成本（token 费用、
时间）、对话速度、记忆效果及是否准确使用。

你的任务：实现记忆系统模块 agent/memory.py。这是整个项目的核心评审模块。

【文件边界——严格遵守】
- 你只能创建/修改以下文件：
  - agent/memory.py（已有接口 stub，填充实现，函数签名不许改）
  - agent/test_memory.py（你写的自测脚本）
- 禁止改动 tab_engine/、web/、server.py、scripts/ 下的任何文件（其他 AI 在并行开发）
- 运行时产生的数据文件放在 data/ 目录（代码里自动创建）

【需要实现的三个函数（签名固定，见 agent/memory.py stub）】
1. retrieve(query: str) -> str
   检索与当前任务相关的记忆，拼装为注入 system prompt 的中文字符串，格式：
   【用户画像】水平:中级 | 大横按:困难 | 设备:Tele+综合效果器
   【相关规则】1. 十六分扫弦降级为八分 2. 失真度不超过60%
   【相似经历】上次弹《蓝色星球》第12小节跨把位失败，已改为滑弦
   要求：画像层全量注入；规则层按 query 向量相似度取 top-3；情景层取 top-2；
   每层注入条数必须可通过参数配置（控制 token 成本是考查点）。

2. distill(user_input: str, agent_output: str, user_feedback: str) -> None
   用 LLM 从用户反馈中提炼记忆，写入对应层：
   - 偏好/限制类 → 更新画像层 profile.json（如"我按不了大横按"→ 手型限制）
   - 规则类 → 追加到 rules.json，写入前用向量相似度去重合并（阈值 0.85）
   - 具体事件 → 写入情景层向量库 episodes.db
   LLM 提炼 prompt 要求输出结构化 JSON：{"type": "profile"|"rule"|"episode"|"none", "content": "..."}
   无提炼价值时返回 none，不写入。

3. get_memory_snapshot() -> dict
   返回三层记忆完整内容 + 累计成本统计（总token、总耗时、记忆条数），
   供前端记忆面板展示，格式自定但要清晰。

【三层记忆存储设计】
- 画像层  data/profile.json：扁平 JSON，如 {"level":"中级","no_barre":true,"gear":"Tele+综合效果器","tone_pref":"轻过载"}
- 规则层  data/rules.json：[{"id","text","created_at","hit_count"}]
- 情景层  data/episodes.db：sqlite-vec 向量库，表结构 (id, input, feedback, embedding, created_at)

【embedding 方案】
为控制成本和依赖，embedding 用简单方案即可：
优先调用 LLM 服务的 embedding 接口（OpenAI 兼容 /embeddings）；
若不可用，降级为字符级 n-gram 哈希向量（自己实现，维度 512），保证离线可跑。

【LLM 调用约定】
- 用 openai Python SDK（OpenAI 兼容协议），禁止硬编码 key：
  client = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY"))
  模型名从 os.getenv("LLM_MODEL", "deepseek-chat") 读取
- distill 必须支持异步调用：函数本身保持同步签名，但内部实现要轻量快速
  （调用方会放在独立线程中执行）

【成本埋点（评审数据，必须做）】
每次 LLM 调用、每次记忆读写，追加一行 JSON 到 data/memory_log.jsonl：
{"ts": "...", "op": "distill|retrieve", "tokens_in": n, "tokens_out": n,
 "latency_ms": n, "detail": "..."}

【自测要求】
写 agent/test_memory.py，模拟以下流程并打印每步结果：
1. 首次 retrieve（记忆为空，应返回空或提示无记忆）
2. distill("我想弹God Knows", "...(Agent输出)", "这段solo太快了，我弹不了十六分音符")
   → 应提炼出规则并写入
3. distill(..., ..., "我不喜欢高增益音色") → 应更新画像音色偏好
4. retrieve("我想弹空箱") → 必须命中第2步的规则（相似任务：都是生成谱子）
5. 打印 get_memory_snapshot() 和 memory_log.jsonl 的成本统计
验收标准：python agent/test_memory.py 跑通，第4步能看到规则被正确检索，
且日志里有完整的 token/耗时数据。

【质量要求】
- 代码加必要的中文注释
- 所有文件 IO 做异常容错（文件不存在时初始化空数据）
- 不要过度设计，不加 stub 之外的抽象
完成后请把 memory.py 和 test_memory.py 的完整代码输出给我。
```

## 交付物

- `agent/memory.py` 完整实现
- `agent/test_memory.py` 自测脚本

## 回收任务时的检查清单

1. `python agent/test_memory.py` 能跑通且第 4 步命中规则
2. 函数签名与 stub 完全一致（我的 Agent 主链路要直接调用）
3. `data/memory_log.jsonl` 有 token/耗时埋点数据
4. 没有改动 stub 之外的文件
