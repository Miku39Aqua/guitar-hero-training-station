"""快速测试 DeepSeek API 连通性和速度"""
import time
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.getenv("LLM_API_KEY", ""),
    timeout=45,
)

# 测试 flash 模型
for model in ["deepseek-v4-flash", "deepseek-v4-pro"]:
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "输出一个JSON对象 {\"ok\": true}"}],
            temperature=0,
            max_tokens=50,
        )
        print(f"[{model}] 耗时 {time.time()-start:.1f}s | 回复: {resp.choices[0].message.content[:80]}")
    except Exception as e:
        print(f"[{model}] 耗时 {time.time()-start:.1f}s | 失败: {type(e).__name__}: {str(e)[:150]}")
