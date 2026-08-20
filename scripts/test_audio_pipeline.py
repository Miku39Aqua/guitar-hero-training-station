"""测试音频管线完整流程：上传 → 后端 chat 带 audio_filename → 看 alphaTex"""
import urllib.request
import urllib.parse
import json

# 1. 上传
boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00" + b"\x00" * 100

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="test.wav"\r\n'
    f"Content-Type: audio/wav\r\n\r\n"
).encode() + wav_data + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    "http://localhost:8000/api/upload",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)
resp = urllib.request.urlopen(req, timeout=30)
upload_result = json.loads(resp.read().decode())
print(f"上传结果: {upload_result}")

# 2. 调用 /api/chat
chat_body = json.dumps({"message": "", "audio_filename": upload_result["filename"]}).encode()
req2 = urllib.request.Request(
    "http://localhost:8000/api/chat",
    data=chat_body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
resp2 = urllib.request.urlopen(req2, timeout=30)
chat_result = json.loads(resp2.read().decode())
print(f"task_id: {chat_result.get('task_id')}")

# 3. 轮询
import time
task_id = chat_result["task_id"]
for i in range(10):
    time.sleep(3)
    req3 = urllib.request.Request(f"http://localhost:8000/api/tasks/{task_id}", method="GET")
    resp3 = urllib.request.urlopen(req3, timeout=30)
    task_data = json.loads(resp3.read().decode())
    print(f"[{(i+1)*3}s] status={task_data.get('status')} progress={task_data.get('progress', '')[:60]}")
    if task_data.get("status") in ("done", "failed"):
        if "alphatex" in task_data:
            print(f"alphaTex 前 200 字: {task_data['alphatex'][:200]}")
        break
