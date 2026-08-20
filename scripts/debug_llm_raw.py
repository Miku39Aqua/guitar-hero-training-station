"""调试：打印 LLM 原始返回内容"""
import time
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.getenv("LLM_API_KEY", ""),
    timeout=60,
)

prompt = """你是一个 ACG 吉他谱生成助手。生成一个简短的吉他谱片段（演示用）。

用户想弹：我想弹 God Knows

请输出 JSON：
{
    "title": "曲名",
    "artist": "艺术家",
    "bpm": 120,
    "measures": [
        {"beats": [
            {"duration": 4, "notes": [{"string": 3, "fret": 0}]},
            {"duration": 4, "notes": []}
        ]}
    ]
}

严格约束（必须遵守）：
- 只生成开头片段，恰好 4 个小节，不多不少
- 每个小节恰好 4 个 beat
- 每个 beat 的 notes 最多 2 个音符
- 只输出 JSON，不要其他任何内容，不要解释
"""

for model in ["deepseek-v4-flash", "deepseek-v4-pro"]:
    start = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000,
    )
    elapsed = time.time() - start
    msg = resp.choices[0].message
    content = msg.content
    reasoning = getattr(msg, "reasoning_content", None)
    finish = resp.choices[0].finish_reason
    usage = resp.usage
    print(f"=== [{model}] 耗时 {elapsed:.1f}s | finish={finish} | out_tokens={usage.completion_tokens}")
    if reasoning:
        print(f"  思考内容前100字: {reasoning[:100]}")
    print(f"  content前300字: {repr(content[:300]) if content else '(空)'}")
    print()
