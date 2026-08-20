"""端到端测试 /api/chat（带计时）"""
import json
import time
import urllib.request

req = urllib.request.Request(
    "http://localhost:8000/api/chat",
    data=json.dumps({"message": "我想弹 God Knows"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

start = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=320)
    elapsed = time.time() - start
    data = json.loads(resp.read())
    print(f"耗时 {elapsed:.1f}s")
    print("Reply:", data["reply"][:200])
    print()
    print("AlphaTex:")
    print(data["alphatex"][:500])
except Exception as e:
    print(f"耗时 {time.time()-start:.1f}s | 失败: {type(e).__name__}: {e}")
