"""测试禁用思考 + 精简 prompt 的效果"""
import time
import json
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.getenv("LLM_API_KEY", ""),
    timeout=60,
)

base_prompt = """你是 ACG 吉他谱生成助手。为用户想弹的曲子生成开头片段。

用户想弹：我想弹 God Knows

输出 JSON：
{"title": "曲名", "artist": "艺术家", "bpm": 120, "measures": [{"beats": [{"duration": 4, "notes": [{"string": 3, "fret": 0}]}, {"duration": 4, "notes": []}]}]}

约束：
- 恰好 4 个小节，每小节 4 个 beat，每 beat 最多 2 个音符
- duration: 4=四分 8=八分；string: 1-6（1=高音e）；fret: 0-12
- 只输出 JSON，不要解释
"""

tests = [
    ("精简prompt+禁思考(enable_thinking)", {"extra_body": {"enable_thinking": False}}),
    ("精简prompt+禁思考(thinking disabled)", {"extra_body": {"thinking": {"type": "disabled"}}}),
    ("精简prompt 原样", {}),
]

for name, extra in tests:
    start = time.time()
    try:
        kwargs = dict(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": base_prompt}],
            temperature=0.7,
            max_tokens=4000,
        )
        kwargs.update(extra)
        resp = client.chat.completions.create(**kwargs)
        elapsed = time.time() - start
        content = (resp.choices[0].message.content or "").strip()
        finish = resp.choices[0].finish_reason
        ok = False
        n = 0
        if "{" in content and "}" in content:
            try:
                data = json.loads(content[content.find("{"):content.rfind("}") + 1])
                n = len(data.get("measures", []))
                ok = True
            except Exception:
                pass
        print(f"[{name}] {elapsed:.1f}s finish={finish} json_ok={ok} 小节={n} len={len(content)}")
    except Exception as e:
        print(f"[{name}] {time.time()-start:.1f}s 失败: {type(e).__name__}: {str(e)[:100]}")
