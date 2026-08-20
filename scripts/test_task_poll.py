"""测试后台任务 API"""
import json
import time
import urllib.request

# 1. 提交任务
req = urllib.request.Request(
    "http://localhost:8000/api/chat",
    data=json.dumps({"message": "我想弹 God Knows"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
resp = urllib.request.urlopen(req, timeout=30)
data = json.loads(resp.read())
task_id = data["task_id"]
print(f"提交成功，task_id={task_id}")

# 2. 轮询任务状态
for i in range(5):
    time.sleep(3)
    poll_req = urllib.request.Request(f"http://localhost:8000/api/tasks/{task_id}", method="GET")
    poll_resp = urllib.request.urlopen(poll_req, timeout=30)
    task_data = json.loads(poll_resp.read())
    print(f"[{(i+1)*3}s] status={task_data['status']} progress={task_data.get('progress', '')[:50]}")
    if task_data["status"] in ("done", "failed"):
        if task_data["status"] == "done":
            print(f"Reply: {task_data['reply'][:100]}")
            print(f"AlphaTex 前100字: {task_data['alphatex'][:100]}")
        else:
            print(f"Error: {task_data.get('error')}")
        break
