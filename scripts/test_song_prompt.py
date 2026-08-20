"""测试新约束 prompt 的生成速度和输出规模"""
import time
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.getenv("LLM_API_KEY", ""),
    timeout=60,
)

memory_context = """【用户画像】音色偏好:不喜欢高增益音色
【相关规则】1. 弹不了十六分音符"""

prompt = f"""你是一个 ACG 吉他谱生成助手。根据用户想弹的曲子，生成一个简短的吉他谱片段（演示用）。

{memory_context}

用户想弹：我想弹 God Knows

请输出 JSON：
{{
    "title": "曲名",
    "artist": "艺术家",
    "bpm": 120,
    "measures": [
        {{"beats": [
            {{"duration": 4, "notes": [{{"string": 3, "fret": 0}}]}},
            {{"duration": 4, "notes": []}}
        ]}}
    ]
}}

严格约束（必须遵守）：
- 只生成开头片段，恰好 4 个小节，不多不少
- 每个小节恰好 4 个 beat
- 每个 beat 的 notes 最多 2 个音符（单音或双音）
- duration: 4=四分音符, 8=八分音符, 2=二分音符
- string: 1-6 (1是高音e弦)
- fret: 0-12 (低把位)
- 空 notes 数组表示休止符
- 只输出 JSON，不要其他任何内容，不要解释

示例规模参考（这就是全部输出的大小）：
{{"title": "x", "artist": "y", "bpm": 120, "measures": [{{"beats": [{{"duration": 4, "notes": [{{"string": 3, "fret": 0}}]}}, {{"duration": 4, "notes": []}}]}}]}}
"""

for model in ["deepseek-v4-flash", "deepseek-v4-pro"]:
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1200,
        )
        elapsed = time.time() - start
        content = resp.choices[0].message.content
        usage = resp.usage
        # 验证 JSON 可解析
        import json
        c = content.strip()
        if c.startswith("```"):
            c = c.split("\n", 1)[1]
        if c.endswith("```"):
            c = c[:-3]
        data = json.loads(c.strip())
        n_measures = len(data.get("measures", []))
        print(f"[{model}] 耗时 {elapsed:.1f}s | tokens: out={usage.completion_tokens} | 小节数={n_measures} | JSON解析 OK")
    except Exception as e:
        print(f"[{model}] 耗时 {time.time()-start:.1f}s | 失败: {type(e).__name__}: {str(e)[:120]}")
