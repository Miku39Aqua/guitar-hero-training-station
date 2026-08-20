"""记忆系统自测脚本

模拟以下流程：
1. 首次 retrieve（记忆为空，应返回空）
2. distill 反馈1 → 规则
3. distill 反馈2 → 画像
4. retrieve → 必须命中第2步的规则
5. 打印快照与日志
"""

import os
import sys
import json
import importlib.util
from pathlib import Path
from unittest.mock import patch

# ========== 路径 ==========
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MEMORY_PY = Path(__file__).resolve().parent / "memory.py"

# ========== 清理旧测试数据 ==========
for f in ["profile.json", "rules.json", "episodes.db", "memory_log.jsonl"]:
    p = DATA_DIR / f
    if p.exists():
        p.unlink()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ========== 环境变量 ==========
os.environ["LLM_BASE_URL"] = "http://localhost:9999"
os.environ["LLM_API_KEY"] = "test-key"
os.environ["LLM_MODEL"] = "deepseek-chat"

# ========== 直接加载 memory.py（不需要 __init__.py） ==========
spec = importlib.util.spec_from_file_location("memory", str(MEMORY_PY))
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)

# 重置 LLM 可用标记
memory._llm_available = True


# ========== Mock 函数 ==========
def mock_embedding(text: str) -> list:
    """模拟 embedding：基于关键词的 512 维向量"""
    vec = [0.0] * 512
    keywords = ["弹", "十六分", "音符", "八分", "空箱", "god", "knows"]
    for kw in keywords:
        if kw in text.lower():
            idx = abs(hash(kw)) % 512
            vec[idx] = 1.0
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def mock_llm_distill(user_input: str, agent_output: str, user_feedback: str):
    """模拟 LLM 提炼"""
    fb = user_feedback
    if "十六分" in fb or "太快" in fb:
        return {"type": "rule", "content": "弹不了十六分音符"}
    elif "不喜欢" in fb and ("音色" in fb or "增益" in fb):
        return {"type": "profile", "content": "音色偏好:不喜欢高增益音色"}
    return {"type": "none", "content": ""}


# ========== 测试流程 ==========
def main():
    print("=" * 60)
    print("记忆系统自测开始")
    print("=" * 60)

    with patch.object(memory, '_get_embedding', side_effect=mock_embedding), \
         patch.object(memory, '_call_llm_for_distill', side_effect=mock_llm_distill):

        # 步骤 1：首次 retrieve（记忆为空）
        print("\n[步骤 1] 首次 retrieve（记忆为空）")
        result = memory.retrieve("")
        print(f"结果: {repr(result)}")
        assert result == "", "记忆为空时应返回空字符串"

        # 步骤 2：distill 反馈1 → 规则
        print("\n[步骤 2] distill 反馈: '这段solo太快了，我弹不了十六分音符'")
        memory.distill("我想弹God Knows", "...", "这段solo太快了，我弹不了十六分音符")
        print("已写入规则")

        # 步骤 3：distill 反馈2 → 画像
        print("\n[步骤 3] distill 反馈: '我不喜欢高增益音色'")
        memory.distill("...", "...", "我不喜欢高增益音色")
        print("已更新画像")

        # 步骤 4：retrieve "我想弹空箱" → 应命中第2步的规则
        print("\n[步骤 4] retrieve('我想弹空箱') → 应命中规则")
        result = memory.retrieve("我想弹空箱")
        print(f"检索结果:\n{result}")
        assert "弹不了十六分音符" in result, "第4步应命中第2步的规则"

        # 步骤 5：打印快照和日志统计
        print("\n[步骤 5] get_memory_snapshot() 与 memory_log.jsonl 成本统计")
        snapshot = memory.get_memory_snapshot()
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))

        # 打印日志
        log_path = DATA_DIR / "memory_log.jsonl"
        if log_path.exists():
            print(f"\n{log_path} 内容:")
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    print(line.strip())

    print("\n" + "=" * 60)
    print("自测通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
